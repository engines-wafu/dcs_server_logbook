from config import *
from database.db_crud import *
from datetime import datetime, timedelta
from discord.ext import commands
from discord.ext.commands import has_role, CheckFailure
from fuzzywuzzy import process, fuzz
from html_generator.html_generator import generate_index_html, load_combined_stats, generate_flight_plans_page
from main import update_logbook_report
from utils.discord_utils import *
from utils.ribbon import *
from utils.stat_processing import get_pilot_qualifications_with_details, get_pilot_awards_with_details, get_pilot_details
from utils.stats_analysis import generate_pilot_hour_report
from utils.time_management import epoch_from_date

import asyncio
import datetime
import discord
import logging
import math
import os
import shutil
import string
import subprocess
import time
import tracemalloc

# Get the absolute path of the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Log file path
log_filename = os.path.join(project_root, "data/logs/bot.log")

# Ensure the log directory exists
os.makedirs(os.path.dirname(log_filename), exist_ok=True)

# Configure a separate logger for your bot
logger = logging.getLogger('my_bot')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(filename=log_filename)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Use this logger for your debug messages
logger.debug("Bot script started.")

tracemalloc.start()

output_path = 'html/index.html'
json_path = 'data/stats/combinedStats.json'
award_messages = {}
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
predefined_colors = PREDEFINED_COLORS

# Hardcoded test
test_name = "engines"
pilot_name = "Engines"
normalized_test_name = ''.join(ch.lower() for ch in test_name if ch.isalnum())
normalized_pilot_name = ''.join(ch.lower() for ch in pilot_name if ch.isalnum())

# Perform a direct fuzzy match
score = fuzz.ratio(normalized_test_name, normalized_pilot_name)
logger.debug(f"Test match score between '{normalized_test_name}' and '{normalized_pilot_name}': {score}")

def update_mayfly_html():
    try:
        # Copy SlmodStats files from their respective locations
        shutil.copy(r"C:\Users\JointStrikeWing\Saved Games\DCS.openbeta_server\Slmod\SlmodStats.json",
                    r"C:\dcs_server_logbook\data\stats\SlmodStats_server1.json")
        shutil.copy(r"C:\Users\JointStrikeWing\Saved Games\DCS.openbeta_server2\Slmod\SlmodStats.json",
                    r"C:\dcs_server_logbook\data\stats\SlmodStats_server2.json")
        shutil.copy(r"C:\Users\JointStrikeWing\Saved Games\DCS.openbeta_server3\Slmod\SlmodStats.json",
                    r"C:\dcs_server_logbook\data\stats\SlmodStats_server3.json")

        # Set the current working directory to the project root
        os.chdir(r"C:\dcs_server_logbook")

        # Run the Python script
        subprocess.run(["python", r"src\main.py"], check=True)

        print("Mayfly HTML update completed successfully!")
        return True
    except (shutil.Error, subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Failed to update Mayfly HTML: {e}")
        return False

def is_commanding_officer():
    async def predicate(ctx):
        return any(role.name in {COMMANDING_OFFICER, HQ_ROLE} for role in ctx.author.roles)
    return commands.check(predicate)

def is_server_admin():
    async def predicate(ctx):
        return any(role.name == SERVER_ADMIN for role in ctx.author.roles)
    return commands.check(predicate)

async def fuzzy_match_pilot_to_discord_user(ctx, pilot_name):
    """
    Perform a fuzzy search to match a pilot name to a Discord user ID,
    accounting for possible rank prefixes in Discord user names.
    """
    if pilot_name is None:
        logger.error("Pilot name is None")
        return None

    rank_prefixes = ['slt', 'lt', 'ltcdr', 'cdr', '2lt', 'lt', 'cpt', 'maj', 'ltcol', 'col', 'pltoff', 'flgoff', 'fltlt', 'sqnldr', 'wgcdr']  # Add or remove ranks as needed

    def normalize_name(name):
        # Lowercase and remove whitespace and punctuation
        normalized = ''.join(ch.lower() for ch in name if ch.isalnum())
        # Remove common rank prefixes
        for prefix in rank_prefixes:
            if normalized.startswith(prefix):
                return normalized[len(prefix):]
        return normalized

    try:
        # Retrieve all Discord users from the guild
        all_discord_users = await get_all_discord_users(ctx.guild)
    except Exception as e:
        logger.error(f"Error retrieving Discord users: {e}")
        return None

    # Normalize names and create a mapping of names to IDs
    valid_members = {normalize_name(user.display_name): user.id for user in all_discord_users if user and user.display_name}

    # Normalize pilot_name
    normalized_pilot_name = normalize_name(pilot_name)

    highest_score = 0
    best_match_id = None

    # Perform manual comparisons and find the best match
    for discord_name, discord_id in valid_members.items():
        score = fuzz.ratio(normalized_pilot_name, discord_name)

        if score > highest_score:
            highest_score = score
            best_match_id = discord_id

    if highest_score > 60:  # Adjust the threshold as needed
        return best_match_id
    else:
        return None


async def get_all_discord_users(guild):
    """
    Retrieves all users from the given guild (server).

    :param guild: The discord Guild (server) object.
    :return: A list of Member objects.
    """
    members = []
    async for member in guild.fetch_members(limit=None):
        members.append(member)
    return members

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.send("You do not have the required role to use this command.")
    else:
        raise error  # Re-raise other errors so you can notice them

@bot.event
async def on_reaction_add(reaction, user):
    # Ignore the bot's own reactions and other messages
    if user.bot or reaction.message.id not in award_messages:
        return

    # Retrieve the state for the current message
    message_info = award_messages[reaction.message.id]
    current_page = message_info['page']
    total_pages = message_info['total_pages']
    awards = message_info['awards']
    items_per_page = message_info['items_per_page']  # Retrieve items_per_page

    # Check which reaction was added and update the page number
    if str(reaction.emoji) == "⬅️" and current_page > 1:
        current_page -= 1
    elif str(reaction.emoji) == "➡️" and current_page < total_pages:
        current_page += 1
    else:
        return  # If it's not one of the navigation reactions, ignore

    # Edit the message with the new embed for the updated page
    embed = create_awards_embed(awards, current_page, items_per_page)
    await reaction.message.edit(embed=embed)

    # Update the global dictionary with the new current page
    award_messages[reaction.message.id]['page'] = current_page

    # Remove the reaction to allow for re-use
    await reaction.message.remove_reaction(reaction.emoji, user)

def chunk_report(report_sections):
    # Convert the report sections into pages
    return report_sections  # Each section is now a page

def create_qualifications_embed(qualifications, current_page, items_per_page):
    """
    Creates a Discord embed for a paginated list of qualifications.

    :param qualifications: A list of qualifications (tuple of qualification ID, name, and duration).
    :param current_page: The current page number.
    :param items_per_page: The number of items to display per page.
    :return: A Discord Embed object containing the qualifications for the current page.
    """
    start_index = (current_page - 1) * items_per_page
    end_index = start_index + items_per_page
    paginated_qualifications = qualifications[start_index:end_index]

    embed = discord.Embed(title="Available Qualifications", description="Select a qualification by its ID.", color=0x00ff00)
    for qid, qname, _ in paginated_qualifications:
        embed.add_field(name=str(qid), value=qname, inline=False)

    # Optionally, you can add footer text to show the current page number
    embed.set_footer(text=f"Page {current_page} of {(len(qualifications) + items_per_page - 1) // items_per_page}")

    return embed

def create_awards_embed(awards, page, items_per_page=ITEMS_PER_PAGE):
    embed = discord.Embed(title=f"Available Awards - Page {page}", color=0x00ff00)
    page_start = (page - 1) * items_per_page
    page_end = page_start + items_per_page
    for aid, aname in awards[page_start:page_end]:
        embed.add_field(name=f"ID: {aid}", value=aname, inline=False)
    return embed

def generate_single_ribbon(award_name, file_path, min_block_width_percent=10, max_block_width_percent=30):
    pattern_generator = ribbonGenerator(
        award_name,
        color_array=predefined_colors,
        min_block_width_percent=min_block_width_percent,
        max_block_width_percent=max_block_width_percent
    )
    pattern_generator.save_pattern_as_png(file_path)

# Helper function to prompt for input in DMs and return response
async def prompt_for_details(ctx, prompt_text):
    """
    Sends a prompt to the user in DM and waits for a response.
    Returns the response content, or None if no response is given.
    """
    try:
        await ctx.author.send(prompt_text)
        message = await bot.wait_for('message', timeout=90.0, check=lambda m: m.author == ctx.author and isinstance(m.channel, discord.DMChannel))
        return message.content
    except asyncio.TimeoutError:
        await ctx.author.send("You did not respond in time.")
        return None

async def get_response(ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=90.0)
        return response.content
    except asyncio.TimeoutError:
        await ctx.send("You did not respond in time.")
        return None

@bot.command(name='add_pilot')
@is_commanding_officer()
async def add_pilot_command(ctx):
    """
    Adds a new pilot to the database, with details collected via direct messages (DMs).

    This command guides the user through the process of adding a new pilot by prompting for necessary information such as pilot ID, name, service branch, and rank. The process is conducted through DMs for privacy. Once all details are provided, the new pilot is added to the database, and a confirmation is sent in an embedded message format.

    Usage: !add_pilot

    Example:
    User: !add_pilot
    Bot: [In DMs] Please enter the pilot ID:
    User: [Responds in DMs with each detail as prompted]
    Bot: [In server] Pilot Added Successfully [with detailed embed]
    """
    details = {}
    fields = [
        ("pilot ID", None),
        ("pilot name", None),
        ("pilot service branch (e.g., RN, Army, RAF)", ['RN', 'Army', 'RAF']),
        ("pilot rank", None)
    ]

    for field, validation in fields:
        response = await prompt_for_details(ctx, f"Please enter the {field}:")
        if not response:
            await ctx.author.send("No response provided. Exiting command.")
            return

        if isinstance(validation, list) and response not in validation:
            await ctx.author.send(f"Invalid input. Please choose from {validation}.")
            return
        else:
            details[field] = response

    # Construct and send the confirmation embed via DM
    embed = discord.Embed(title="Please Confirm Pilot Details", color=0x00ff00)
    for field, value in details.items():
        embed.add_field(name=field.capitalize(), value=value, inline=False)

    dm_channel = await ctx.author.create_dm()
    confirmation_message = await dm_channel.send(embed=embed)
    await confirmation_message.add_reaction("✅")
    await confirmation_message.add_reaction("❌")

    # Check for user's reaction in DM
    def check(reaction, user):
        return user == ctx.author and reaction.message.id == confirmation_message.id and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            # User confirmed, proceed with adding to database
            loop = asyncio.get_event_loop()
            insert_success = await loop.run_in_executor(None, add_pilot_to_db, 
                                                       DB_PATH, 
                                                       details["pilot ID"], 
                                                       details["pilot name"], 
                                                       details["pilot service branch (e.g., RN, Army, RAF)"], 
                                                       details["pilot rank"])
            if insert_success:
                logger.info(f"Pilot {details['pilot ID']} added successfully to the database.")
                await ctx.send(embed=embed)  # Send confirmation in the text channel
            else:
                logger.warning(f"Failed to add Pilot {details['pilot ID']} to the database.")
                await ctx.author.send("Failed to add the pilot.")
        elif str(reaction.emoji) == "❌":
            await ctx.author.send("Pilot addition canceled.")
    except asyncio.TimeoutError:
        await ctx.author.send("No response received. Pilot addition canceled.")

@bot.command(name='add_squadron')
@is_server_admin()
async def add_squadron_command(ctx):
    """
    Adds a new squadron to the database, with details collected via direct messages (DMs).

    This command initiates a process to add a new squadron to the database. The user is prompted to provide various details about the squadron through DMs, ensuring privacy and data integrity. The bot collects information such as the squadron ID, motto, service branch, commission date, commanding officer, aircraft type, and pseudo type.

    Once all the necessary information is collected, the bot sends a confirmation message back to the user in DMs, displaying all the entered details in an embedded message format. The user can then review these details and either confirm or cancel the addition of the squadron to the database.

    If the user confirms, the bot proceeds to add the squadron to the database and then sends a confirmation message in the public text channel where the command was initially invoked, indicating the successful addition. If the user cancels or fails to respond, the process is terminated, and no changes are made to the database.

    Usage:
    User invokes the command in a text channel: 
    !add_squadron

    Bot responds via DM and guides the user through the data entry process.

    Example Interaction:
    User: !add_squadron
    Bot: [In DMs] Please enter the squadron ID:
    User: [Responds in DMs] 101
    Bot: [In DMs] Please enter the squadron motto:
    User: [Responds in DMs] Semper Paratus
    ... [further data collection interactions]
    Bot: [In DMs] Here are the details you entered: [Shows Embed]
    User: [Reacts with ✅ or ❌ in DMs]
    Bot: [In server channel if ✅] Squadron 101 added successfully.

    Note:
    - The user must react with ✅ to confirm or ❌ to cancel the addition.
    - If the user does not react within 60 seconds, the operation is automatically canceled.
    - The user can restart the process by invoking the command again.
    """
    logger.info("Starting to collect squadron details via DMs.")
    details = {}
    fields = [
        ("squadron ID", None),
        ("squadron motto", None),
        ("squadron service branch (e.g., RN, Army, RAF)", ['RN', 'Army', 'RAF']),
        ("squadron commission date (YYYY-MM-DD)", "date"),
        ("name of the commanding officer", None),
        ("squadron aircraft type", None),
        ("squadron pseudo type", None)
    ]

    for field, validation in fields:
        response = await prompt_for_details(ctx, f"Please enter the {field}:")
        if not response:
            await ctx.author.send("No response provided. Exiting command.")
            return

        if validation == "date":
            try:
                commission_date_obj = datetime.datetime.strptime(response, "%Y-%m-%d")
                details[field] = commission_date_obj.strftime("%Y-%m-%d")  # Store as string for display
            except ValueError:
                await ctx.author.send("Invalid date format. Please use YYYY-MM-DD.")
                return
        elif isinstance(validation, list) and response not in validation:
            await ctx.author.send(f"Invalid input. Please choose from {validation}.")
            return
        else:
            details[field] = response

    # Construct and send the confirmation embed via DM
    embed = discord.Embed(title="Please Confirm Squadron Details", color=0x00ff00)
    for field, value in details.items():
        embed.add_field(name=field.capitalize(), value=value, inline=False)

    dm_channel = await ctx.author.create_dm()
    confirmation_message = await dm_channel.send(embed=embed)
    await confirmation_message.add_reaction("✅")
    await confirmation_message.add_reaction("❌")

    # Check for user's reaction in DM
    def check(reaction, user):
        return user == ctx.author and reaction.message.id == confirmation_message.id and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            # User confirmed, proceed with adding to database
            loop = asyncio.get_event_loop()
            insert_success = await loop.run_in_executor(None, add_squadron_to_db, DB_PATH, *details.values())
            if insert_success:
                logger.info(f"Squadron {details['squadron ID']} added successfully to the database.")
                await ctx.send(embed=embed)  # Send confirmation in the text channel
            else:
                logger.warning(f"Failed to add Squadron {details['squadron ID']} to the database.")
                await ctx.author.send("Failed to add the squadron.")
        elif str(reaction.emoji) == "❌":
            # User denied, start data entry process again or exit
            await ctx.author.send("Data entry canceled. Please start over with !add_squadron.")
    except asyncio.TimeoutError:
        await ctx.author.send("No response received. Squadron addition canceled.")

@bot.command(name='edit_pilot')
@is_server_admin()
async def edit_pilot_command(ctx, pilot_name: str):
    """
    Edits an existing pilot's details in the database.

    This command allows server admins to update the details of a pilot by specifying the pilot's name. 
    Upon invocation with a pilot's name, the bot prompts the admin to update various details of the pilot, 
    such as their service branch and rank. The admin can confirm or cancel these updates.

    Usage: 
    !edit_pilot [pilot_name]

    Example:
    User: !edit_pilot JohnDoe
    Bot: [Prompts for updates in DMs]
    User: [Responds with updated details]
    Bot: [Shows confirmation embed]
    User: [Confirms the updates]
    """

    # Find the pilot ID by name
    pilot_id = find_pilot_id_by_name(DB_PATH, pilot_name)
    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return

    # Load combined stats from the JSON file
    combined_stats = load_combined_stats(JSON_PATH)

    # Fetch current details of the pilot
    current_details = get_pilot_details(DB_PATH, pilot_id, combined_stats)
    if not current_details:
        await ctx.send(f"No details found for Pilot: {pilot_name}.")
        return

    # Create a Direct Message channel with the user
    dm_channel = await ctx.author.create_dm()

    # Fields that can be edited
    editable_fields = ["name", "service", "rank"]

    # Collect new details from the user
    new_details = {}
    for field in editable_fields:
        new_value = await prompt_for_details(ctx, f"Enter the new {field} (or type 'skip' to keep current):")
        if new_value.lower() != 'skip':
            new_details[field] = new_value

    # Construct confirmation embed with new details
    confirm_embed = discord.Embed(title="Confirm Pilot Updates", color=0x00ff00)
    for field, value in new_details.items():
        confirm_embed.add_field(name=field.capitalize(), value=value, inline=False)
    confirm_message = await dm_channel.send(embed=confirm_embed)
    await confirm_message.add_reaction("✅")
    await confirm_message.add_reaction("❌")

    # Check for user's reaction
    def check(reaction, user):
        return user == ctx.author and reaction.message.id == confirm_message.id and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            # User confirmed, update details in database
            update_success = update_pilot(DB_PATH, pilot_id, new_details)
            if update_success:
                await ctx.send(f"Pilot {pilot_name} updated successfully.")
            else:
                await ctx.send("Failed to update the pilot.")
        elif str(reaction.emoji) == "❌":
            await ctx.author.send("Update canceled.")
    except asyncio.TimeoutError:
        await ctx.author.send("No response received. Update canceled.")

@bot.command(name='edit_squadron')
@is_server_admin()
async def edit_squadron_command(ctx):
    """
    Edits an existing squadron's details in the database, with interactions conducted via DMs.

    The command first presents a list of existing squadrons to the user in a DM. The user selects a squadron to edit by specifying its list number. The bot then prompts the user to edit various details of the squadron. Once the user has provided all necessary updates, the bot sends a confirmation message with the updated details in an embedded format. The user confirms the updates, and the bot then commits these changes to the database.

    Usage: !edit_squadron

    Example:
    User: !edit_squadron
    Bot: [In DMs] Here are the available squadrons: [Shows Embed]
    User: [Responds in DMs] 1
    Bot: [In DMs] Please enter the new motto for Squadron [ID]:
    User: [Responds in DMs with updated details]
    Bot: [In DMs] Here are the updated details: [Shows Embed]
    User: [Confirms the details]
    Bot: [In server] Squadron [ID] updated successfully.
    """

    # Fetch list of squadron IDs
    squadrons = get_squadron_ids(DB_PATH)
    if not squadrons:
        await ctx.author.send("No squadrons available to edit.")
        return

    # Send a list of squadrons in an embed via DM
    embed = discord.Embed(title="Available Squadrons", description="Select a squadron to edit by entering its number.", color=0x00ff00)
    for index, squadron_id in enumerate(squadrons, start=1):
        embed.add_field(name=f"Squadron {index}", value=squadron_id, inline=False)
    
    dm_channel = await ctx.author.create_dm()
    squadron_list_message = await dm_channel.send(embed=embed)

    # Prompt user to select a squadron
    selected_squadron = await prompt_for_details(ctx, "Please enter the number of the squadron you wish to edit:")

    # Validate user's choice
    try:
        selected_index = int(selected_squadron) - 1
        if selected_index < 0 or selected_index >= len(squadrons):
            raise ValueError
    except ValueError:
        await dm_channel.send("Invalid selection. Please start over with !edit_squadron.")
        return

    squadron_id = squadrons[selected_index]

    # Prompt for details to edit

    # Assuming 'squadron_id' is the ID of the squadron to be edited
    # Fetch current details of the selected squadron
    current_details = get_squadron_details(DB_PATH, squadron_id)
    if not current_details:
        await dm_channel.send(f"No details found for Squadron ID: {squadron_id}. Please try again.")
        return

    # Fields that can be edited (add more as needed)
    editable_fields = [
        "motto",
        "service branch",
        "commission date",
        "commanding officer",
        "aircraft type",
        "pseudo type"
    ]

    # Collect new details from the user
    new_details = {}
    confirmation_details = {}  # For confirmation message
    for field in editable_fields:
        new_value = await prompt_for_details(ctx, f"Enter the new {field} (or type 'skip' to keep current):")
        if new_value.lower() != 'skip':
            if field == "commission date":
                # Convert date to epoch format for database update
                epoch_value = epoch_from_date(new_value)
                if epoch_value is not None:
                    new_details[field] = epoch_value
                    confirmation_details[field] = new_value  # Keep user-friendly format for confirmation
                else:
                    await dm_channel.send("Invalid date format for commission date. Update canceled.")
                    return
            else:
                new_details[field] = new_value
                confirmation_details[field] = new_value  # Same value for other fields

    # Construct confirmation embed with user-friendly details
    confirm_embed = discord.Embed(title="Confirm Squadron Updates", color=0x00ff00)
    for field, value in confirmation_details.items():
        confirm_embed.add_field(name=field.capitalize(), value=value, inline=False)
    confirm_message = await dm_channel.send(embed=confirm_embed)
    await confirm_message.add_reaction("✅")
    await confirm_message.add_reaction("❌")

    # Check for user's reaction
    def check(reaction, user):
        return user == ctx.author and reaction.message.id == confirm_message.id and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
        if str(reaction.emoji) == "✅":
            # User confirmed, update details in database
            update_success = update_squadron(DB_PATH, squadron_id, new_details)
            if update_success:
                await ctx.send(f"Squadron {squadron_id} updated successfully.")
            else:
                await ctx.send("Failed to update the squadron.")
        elif str(reaction.emoji) == "❌":
            await ctx.author.send("Update canceled.")
    except asyncio.TimeoutError:
        await ctx.author.send("No response received. Update canceled.")

@bot.command(name='remove_pilot')
@is_server_admin()
async def remove_pilot_command(ctx, pilot_name: str):
    """
    Archives a pilot by moving their record from the Pilots table to the Former_Pilots table.

    This command is used to archive pilots who are no longer active. It first verifies the existence of the pilot 
    in the database and then prompts the admin for confirmation before moving the pilot's record to the Former_Pilots table.

    Usage: 
    !remove_pilot [pilot_name]

    Example:
    User: !remove_pilot JohnDoe
    Bot: Are you sure you want to archive Pilot JohnDoe? (Yes/No)
    User: Yes
    Bot: Pilot JohnDoe archived successfully.
    """

    # Find the pilot ID by name
    pilot_id = find_pilot_id_by_name(DB_PATH, pilot_name)
    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return

    # Ask for confirmation
    confirm_message = await ctx.send(f"Are you sure you want to archive Pilot {pilot_name}? (Yes/No)")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

    try:
        message = await bot.wait_for('message', check=check, timeout=30.0)
        if message.content.lower() == "yes":
            # Proceed with moving to Former_Pilots
            if move_pilot_to_former(DB_PATH, pilot_id):
                await ctx.send(f"Pilot {pilot_name} archived successfully.")
            else:
                await ctx.send("Failed to archive the pilot.")
        else:
            await ctx.send("Pilot archiving canceled.")
    except asyncio.TimeoutError:
        await ctx.send("No response received. Pilot archiving canceled.")

@bot.command(name='pilot_info')
async def pilot_info(ctx, *, pilot_name):
    """
    Retrieves and displays information about a specific pilot.
    
    This command searches for a pilot by their name and provides details including service, rank, total hours, last join date, qualifications, and awards. It also generates a ribbon quilt image representing the pilot's awards and includes it in the response.
    
    Usage: !pilot_info <pilot_name>
    
    Parameters:
    pilot_name (str): The name of the pilot to retrieve information for.
    
    Example:
    !pilot_info JohnDoe
    """
    pilot_id = find_pilot_id_by_name(DB_PATH, pilot_name)
    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return

    # Load combined stats and fetch pilot details
    combined_stats = load_combined_stats(JSON_PATH)
    pilot_details = get_pilot_details(DB_PATH, pilot_id, combined_stats)
    if not pilot_details:
        await ctx.send(f"No details found for pilot: {pilot_name}")
        return

    # Use the proper name if available
    pilot_name = get_pilot_name(DB_PATH, pilot_id)

    # Construct the embedded message with pilot details
    embed = discord.Embed(title=f"Pilot Information: {pilot_name}", color=0x00ff00)
    embed.add_field(name="Service", value=pilot_details['service'], inline=True)
    embed.add_field(name="Rank", value=pilot_details['rank'], inline=True)
    embed.add_field(name="Total Hours", value=str(pilot_details['total_hours']), inline=True)
    embed.add_field(name="Last Joined", value=pilot_details['last_join'], inline=True)

    # Add qualifications and awards to the embed
    qualifications = get_pilot_qualifications_with_details(DB_PATH, pilot_id)
    if qualifications:
        qualifications_text = "\n".join(f"{q[1]} (Issued: {q[3]}, Expires: {q[4]})" for q in qualifications)
        embed.add_field(name="Qualifications", value=qualifications_text, inline=False)
    else:
        embed.add_field(name="Qualifications", value="None", inline=False)

    awards = get_pilot_awards_with_details(DB_PATH, pilot_id)
    if awards:
        awards_text = "\n".join(f"{a[1]} (Issued: {a[3]})" for a in awards)
        embed.add_field(name="Awards", value=awards_text, inline=False)
    else:
        embed.add_field(name="Awards", value="None", inline=False)

    # Generate ribbon quilt image
    create_award_quilt(DB_PATH, pilot_id)  # Generate the quilt image

    # Generate ribbon quilt image and prepare the image file to be sent if it exists
    image_path = f'html/img/fruit_salad/{pilot_id}.png'
    if os.path.exists(image_path):
        with open(image_path, 'rb') as img:
            image_file = discord.File(img, filename='fruit_salad.png')
            embed.set_image(url="attachment://fruit_salad.png")
            await ctx.send(file=image_file, embed=embed)
    else:
        await ctx.send(embed=embed)

@bot.command(name='update_logbook')
@is_server_admin()
async def update_logbook(ctx):
    """
    Updates the logbook with the latest data.

    This command triggers an update process that refreshes the logbook with the most current information. It's typically used to ensure that the logbook reflects recent changes or additions.

    Usage: !update_logbook

    Example:
    User: !update_logbook
    Bot: Updating logbook, please wait...
    Bot: Logbook updated successfully.
    """
    try:
        await ctx.send("Updating logbook, please wait...")
        update_logbook_report()  # Call the main function from main.py
        await ctx.send("Logbook updated successfully.")
    except Exception as e:
        await ctx.send(f"An error occurred while updating the logbook: {e}")

@bot.command(name='create_award')
@is_server_admin()
async def create_award(ctx):
    """
    Creates a new award and generates a ribbon for it.
    
    This command prompts the user to enter the name and optional description of a new award. The award is then added to the database, and a ribbon image is generated to represent it.
    
    Usage: !create_award
    
    Example:
    User: !create_award
    Bot: Enter award name:
    User: Outstanding Service
    Bot: Enter award description (optional):
    User: Awarded for exceptional service
    """
    # Ask for award details
    await ctx.send("Enter award name:")
    award_name = await get_response(ctx)

    await ctx.send("Enter award description (optional):")
    award_description = await get_response(ctx)

    # Add award to database
    try:
        add_award_to_database(DB_PATH, award_name, award_description)
        await ctx.send(f"Award '{award_name}' created successfully.")
    except Exception as e:
        await ctx.send(f"Failed to create award: {e}")
    
    # Make the ribbon
    try:
        ribbon_path = 'html/img/ribbons/' + award_name.replace(" ", "_") + '.png'
        # Here you can also pass different min and max width percentages if needed
        generate_single_ribbon(award_name, ribbon_path)
        await ctx.send(f"Ribbon for '{award_name}' created successfully.")
    except Exception as e:
        await ctx.send(f"Failed to create ribbon: {e}")
    
@bot.command(name='create_qualification')
@is_server_admin()
async def create_qualification(ctx):
    """
    Creates a new qualification entry in the database.

    This command prompts the user to enter the name, optional description, and optional duration (in days) of a new qualification. The qualification is then added to the database.

    Usage: !create_qualification

    Example:
    User: !create_qualification
    Bot: Enter qualification name:
    User: Advanced Flight Training
    Bot: Enter qualification description (optional):
    User: Qualification for advanced flight techniques
    Bot: Enter qualification duration in days (optional, enter a number or skip):
    User: 365
    """
    # Ask for qualification details
    await ctx.send("Enter qualification name:")
    qualification_name = await get_response(ctx)
    if not qualification_name:
        return  # Exit if no response

    await ctx.send("Enter qualification description (optional):")
    qualification_description = await get_response(ctx)

    await ctx.send("Enter qualification duration in days (optional, enter a number or skip):")
    qualification_duration_str = await get_response(ctx)
    qualification_duration_days = int(qualification_duration_str) if qualification_duration_str.isdigit() else None

    # Add qualification to database
    try:
        add_qualification_to_database(DB_PATH, qualification_name, qualification_description, qualification_duration_days)
        await ctx.send(f"Qualification '{qualification_name}' created successfully.")
    except Exception as e:
        await ctx.send(f"Failed to create qualification: {e}")

@bot.command(name='give_award')
@is_commanding_officer()
async def give_award(ctx):
    logger.debug("Attempting to give awards")
    awards = await get_awards(DB_PATH)
    if not awards:
        await ctx.send(embed=discord.Embed(description="No awards available.", color=0xff0000))
        return

    # Correctly create a dictionary from the list of tuples
    awards_dict = {str(award[0]): award[1] for award in awards}

    pilot_names_response = await get_and_process_user_input(ctx, "Enter pilot name(s) (comma-separated):")
    if not pilot_names_response:
        return

    await display_awards(ctx, awards)

    award_ids_response = await get_and_process_user_input(ctx, "Enter the award ID(s) from the list above (comma-separated):")
    if not award_ids_response:
        return

    pilot_ids = process_pilot_names(pilot_names_response)
    award_ids = process_award_ids(award_ids_response)

    for pilot_id in pilot_ids:
        await process_pilot_award(ctx, pilot_id, award_ids, awards_dict)

    await ctx.send(embed=discord.Embed(description="Award(s) assigned to selected pilot(s).", color=0x00ff00))

async def get_and_process_user_input(ctx, prompt):
    await ctx.send(prompt)
    return await get_response(ctx)

def process_pilot_names(pilot_names_response):
    return [find_pilot_id_by_name(DB_PATH, name.strip()) for name in pilot_names_response.split(",") if name.strip()]

def process_award_ids(award_ids_response):
    return [int(award_id.strip()) for award_id in award_ids_response.split(",") if award_id.strip()]

async def process_pilot_award(ctx, pilot_id, award_ids, awards_dict):
    pilot_name = get_pilot_name(DB_PATH, pilot_id)
    squadron_details = get_squadron_details(DB_PATH, get_pilot_squadron_id(DB_PATH, pilot_id))

    if squadron_details is None:
        logging.error(f"No squadron details found for pilot ID {pilot_id}")
        return

    for award_id in award_ids:
        assign_award_to_pilot(DB_PATH, pilot_id, award_id)

async def display_awards(ctx, awards):
    current_page = 1
    items_per_page = ITEMS_PER_PAGE
    total_pages = (len(awards) + items_per_page - 1) // items_per_page

    embed = create_awards_embed(awards, current_page, items_per_page)
    message = await ctx.send(embed=embed)

    if total_pages > 1:
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["⬅️", "➡️"] and reaction.message.id == message.id

        while True:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=10.0, check=check)

                if str(reaction.emoji) == "➡️" and current_page < total_pages:
                    current_page += 1
                elif str(reaction.emoji) == "⬅️" and current_page > 1:
                    current_page -= 1
                else:
                    continue

                await message.remove_reaction(reaction, user)
                embed = create_awards_embed(awards, current_page, items_per_page)
                await message.edit(embed=embed)

            except asyncio.TimeoutError:
                break

async def handle_cr_award(ctx, pilot_id, pilot_name, squadron_details):
    cr_role = squadron_details.get("squadron_cr_role")
    lcr_role = squadron_details.get("squadron_lcr_role")

    discord_user_id = await fuzzy_match_pilot_to_discord_user(ctx, pilot_name)
    if discord_user_id:
        guild = ctx.guild
        member = guild.get_member(discord_user_id)
        if member:
            await remove_role_if_exists(member, lcr_role, guild)
            await assign_role_if_exists(member, cr_role, guild, ctx)
        else:
            await ctx.send("Pilot not found in the Discord server.")
    else:
        await ctx.send("Unable to find a matching Discord user.")

async def remove_role_if_exists(member, role_name, guild):
    role = discord.utils.get(guild.roles, name=role_name)
    if role and role in member.roles:
        await member.remove_roles(role)
        logger.debug(f"Removed role '{role_name}' from user {member.name}")

async def assign_role_if_exists(member, role_name, guild, ctx):
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await member.add_roles(role)
        logger.debug(f"Assigned role '{role_name}' to user {member.name}")
        await ctx.send(f"Assigned role '{role_name}' to the pilot.")
    else:
        await ctx.send(f"Role '{role_name}' not found in the Discord server.")

async def handle_lcr_award(ctx, pilot_id, pilot_name, squadron_details):
    lcr_role = squadron_details.get("squadron_lcr_role")

    discord_user_id = await fuzzy_match_pilot_to_discord_user(ctx, pilot_name)
    if discord_user_id:
        guild = ctx.guild
        member = guild.get_member(discord_user_id)
        if member:
            await assign_role_if_exists(member, lcr_role, guild, ctx)
        else:
            await ctx.send("Pilot not found in the Discord server.")
    else:
        await ctx.send("Unable to find a matching Discord user.")

@bot.command(name='give_qualification')
@is_commanding_officer()
async def give_qualification(ctx):
    """
    Assigns a specified qualification to selected pilots, with paginated qualification display.

    This command first displays a list of available qualifications in a paginated format. Users can navigate through the pages using reaction emojis. Once the user views the qualifications, they are prompted to enter the names of the pilots (comma-separated) and the ID of the chosen qualification. The specified qualification is then assigned to the given pilots, along with its duration.

    Usage: !give_qualification

    Example:
    User: !give_qualification
    Bot: [Displays list of available qualifications with pagination]
    [User navigates through pages using reaction emojis]
    Bot: Enter pilot name(s) (comma-separated):
    User: JohnDoe, JaneDoe
    Bot: Enter the qualification ID from the list above:
    User: 1
    """
    # Retrieve available qualifications
    qualifications = get_qualifications(DB_PATH)
    if not qualifications:
        await ctx.send(embed=discord.Embed(description="No qualifications available.", color=0xff0000))
        return

    # Create a dictionary of qualifications
    qualifications_dict = {str(qid): qname for qid, qname, _ in qualifications}

    # Define page variables
    current_page = 1
    items_per_page = ITEMS_PER_PAGE
    total_pages = (len(qualifications) + items_per_page - 1) // items_per_page

    # Create an embed for qualifications
    embed = create_qualifications_embed(qualifications, current_page, items_per_page)

    # Send the initial qualifications list
    message = await ctx.send(embed=embed)

    # Store the message ID and other details for reaction handling
    qualification_messages = {}
    qualification_messages[message.id] = {'page': current_page, 'total_pages': total_pages, 'qualifications': qualifications, 'items_per_page': items_per_page}

    # Add reaction emojis for navigation if there are multiple pages
    if total_pages > 1:
        await message.add_reaction("⬅️")
        await message.add_reaction("➡️")

    # Reaction handling for page navigation (you'll need to implement this logic)
    # ...

    # Get pilot names
    await ctx.send("Enter pilot name(s) (comma-separated):")
    pilot_names_response = await get_response(ctx)
    if not pilot_names_response:
        return

    # Process pilot names and get their IDs
    pilot_ids = [find_pilot_id_by_name(DB_PATH, name.strip()) for name in pilot_names_response.split(",") if name.strip()]

    # Get qualification ID from the user
    await ctx.send("Enter the qualification ID from the list above:")
    qualification_id_response = await get_response(ctx)
    if not qualification_id_response:
        return

    # Process qualification ID
    qualification_id = qualification_id_response.strip()

    # Ensure the qualification ID is valid
    if qualification_id not in qualifications_dict:
        await ctx.send(embed=discord.Embed(description="Invalid qualification ID.", color=0xff0000))
        return

    # Get the qualification duration
    duration = next((duration for qid, _, duration in qualifications if str(qid) == qualification_id), 0)

    # Calculate date_issued and date_expires
    date_issued = int(time.time())
    date_expires = date_issued + duration if duration else None

    # Assign qualification to pilots
    for pilot_id in pilot_ids:
        assign_qualification_to_pilot(DB_PATH, pilot_id, qualification_id, date_issued, date_expires)

    await ctx.send(embed=discord.Embed(description="Qualification assigned to selected pilots.", color=0x00ff00))

@bot.command(name='clear_award')
@is_commanding_officer()
async def clear_award(ctx, *, pilot_name):
    """
    Removes specified awards from a pilot's record.

    This command displays the awards currently assigned to a pilot. The user is then prompted to select which awards to remove by entering their IDs (comma-separated). The selected awards are then removed from the pilot's record.

    Usage: !clear_award <pilot_name>

    Parameters:
    pilot_name (str): The name of the pilot whose awards are to be cleared.

    Example:
    User: !clear_award JohnDoe
    Bot: [Displays JohnDoe's awards]
    Bot: Select award IDs to remove (comma-separated).
    User: 1, 3
    """
    pilot_id = find_pilot_id_by_name(DB_PATH, pilot_name)
    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return

    pilot_awards = get_pilot_awards(DB_PATH, pilot_id)  # Define this function to retrieve pilot's awards
    if not pilot_awards:
        await ctx.send(f"No awards found for pilot: {pilot_name}")
        return

    # Create an embed for pilot's awards
    embed = discord.Embed(title=f"Awards for {pilot_name}", description="Select award IDs to remove (comma-separated).", color=0x00ff00)
    for award_id, award_name in pilot_awards:
        embed.add_field(name=award_id, value=award_name, inline=False)

    await ctx.send(embed=embed)

    # Get user response
    response = await get_response(ctx)
    if not response:
        return

    # Process response and remove selected awards
    selected_awards = [aid.strip() for aid in response.split(',')]
    for aid in selected_awards:
        remove_award_from_pilot(DB_PATH, pilot_id, aid)

    await ctx.send(f"Awards removed from pilot {pilot_name}'s record.")

@bot.command(name='clear_qualification')
@is_commanding_officer()
async def clear_qualification(ctx, *, pilot_name):
    """
    Removes specified qualifications from a pilot's record.

    This command displays the qualifications currently assigned to a pilot. The user is then prompted to select which qualifications to remove by entering their IDs (comma-separated). The selected qualifications are then removed from the pilot's record.

    Usage: !clear_qualification <pilot_name>

    Parameters:
    pilot_name (str): The name of the pilot whose qualifications are to be cleared.

    Example:
    User: !clear_qualification JohnDoe
    Bot: [Displays JohnDoe's qualifications]
    Bot: Select qualification IDs to remove (comma-separated).
    User: 1, 2
    """
    pilot_id = find_pilot_id_by_name(DB_PATH, pilot_name)
    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return

    pilot_qualifications = get_pilot_qualifications(DB_PATH, pilot_id)  # Define this function to retrieve pilot's qualifications
    if not pilot_qualifications:
        await ctx.send(f"No qualifications found for pilot: {pilot_name}")
        return

    # Create an embed for pilot's qualifications
    embed = discord.Embed(title=f"Qualifications for {pilot_name}", description="Select qualification IDs to remove (comma-separated).", color=0x00ff00)
    for qual_id, qual_name in pilot_qualifications:
        embed.add_field(name=qual_id, value=qual_name, inline=False)

    await ctx.send(embed=embed)

    # Get user response
    response = await get_response(ctx)
    if not response:
        return

    # Process response and remove selected qualifications
    selected_qualifications = [qid.strip() for qid in response.split(',')]
    for qid in selected_qualifications:
        remove_qualification_from_pilot(DB_PATH, pilot_id, qid)

    await ctx.send(f"Qualifications removed from pilot {pilot_name}'s record.")

@bot.command(name='assign_co')
@is_server_admin()
async def assign_co(ctx, *, pilot_name):
    """
    Assigns a pilot as the commanding officer (CO) of a squadron.

    This command finds a pilot based on the provided name and displays a list of available squadrons. The user is then prompted to select a squadron number for the pilot to lead as CO.

    Usage: !assign_co <pilot_name>

    Parameters:
    pilot_name (str): The name of the pilot to be assigned as CO.

    Example:
    User: !assign_co JohnDoe
    Bot: [Displays list of squadrons]
    Bot: Select squadron by number:
    User: 1
    """
    pilot_id = find_pilot_id_by_name(DB_PATH, pilot_name)
    pilot_name = get_pilot_full_name(DB_PATH, pilot_id)

    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return
    
    squadrons = get_squadron_ids(DB_PATH)

    if not squadrons:
        await ctx.send("No squadrons available.")
        return

    # Embed for squadron selection
    embed = discord.Embed(title="Squadron Assignment", description="Select squadron by number:", color=0x00ff00)
    for index, squadron_id in enumerate(squadrons, start=1):
        embed.add_field(name=f"{index}.", value=squadron_id, inline=False)

    message = await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=60.0)
        selection = int(response.content.strip()) - 1
        if 0 <= selection < len(squadrons):
            selected_squadron_id = squadrons[selection]
            assign_co_to_squadron(DB_PATH, pilot_id, selected_squadron_id)
            await ctx.send(f"Pilot '{pilot_name}' assigned as CO of '{selected_squadron_id}'.")
        else:
            await ctx.send("Invalid selection. Please enter a valid number.")

    except ValueError:
        await ctx.send("Invalid selection. Please enter valid numbers.")
    except asyncio.TimeoutError:
        await ctx.send("You did not respond in time.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name='assign_pilot')
@is_commanding_officer()
async def assign_pilot(ctx, *, pilot_names):  # Use '*' to capture all text after the command
    """
    Assigns one or more pilots to squadrons.

    This command allows the user to assign multiple pilots to squadrons. The user enters the names of the pilots (comma-separated), and then selects the squadrons for each pilot by entering their numbers (also comma-separated).

    Usage: !assign_pilot <pilot_names>

    Parameters:
    pilot_names (str): The names of the pilots to be assigned, separated by commas.

    Example:
    User: !assign_pilot JohnDoe, JaneDoe
    Bot: [Displays list of squadrons]
    Bot: Select squadrons for the pilots by number:
    User: 1, 2
    """
    pilot_names = [name.strip() for name in pilot_names.split(',')]  # Split and strip pilot names

    pilot_ids = []
    for name in pilot_names:
        pilot_id = find_pilot_id_by_name(DB_PATH, name)
        if pilot_id:
            pilot_ids.append((name, pilot_id))
        else:
            await ctx.send(f"No pilot found with the name: {name}")

    if not pilot_ids:
        return  # Exit if no valid pilots were found

    squadrons = get_squadron_ids(DB_PATH)
    if not squadrons:
        await ctx.send("No squadrons available.")
        return

    embed = discord.Embed(title="Squadron Assignment",
                          description="Select squadrons for the pilots by number:",
                          color=0x00ff00)

    # Add squadrons to the embed as fields
    for index, squadron_id in enumerate(squadrons, start=1):
        embed.add_field(name=f"{index}.", value=squadron_id, inline=False)

    message = await ctx.send(embed=embed)

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=60.0)  # 60 seconds to reply
        selected_indices = [int(num.strip()) for num in response.content.split(',')]
        selected_squadrons = [squadrons[idx - 1] for idx in selected_indices if 1 <= idx <= len(squadrons)]

        for name, pilot_id in pilot_ids:
            name = get_pilot_name(DB_PATH, pilot_id)
            for squadron_id in selected_squadrons:
                assign_pilot_to_squadron(DB_PATH, pilot_id, squadron_id)
            await ctx.send(f"Pilot '{name}' assigned to selected squadrons: {', '.join(selected_squadrons)}.")

    except ValueError:
        await ctx.send("Invalid selection. Please enter valid numbers.")
    except asyncio.TimeoutError:
        await ctx.send("You did not respond in time.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

@bot.command(name='assign_aircraft')
@is_commanding_officer()
async def assign_aircraft(ctx):
    """
    Assigns selected aircraft to a squadron or sends them to maintenance.

    This command first prompts the user to select aircraft by IDs. Then, it offers a choice to assign these aircraft to a specific squadron or send them to maintenance. The user selects a squadron by number or types 'maintenance' to send the aircraft to maintenance.

    Usage: !assign_aircraft

    Example:
    User: !assign_aircraft
    Bot: [Displays list of aircraft]
    Bot: Enter aircraft ID(s) (comma-separated):
    User: 1, 2
    Bot: [Displays list of squadrons and maintenance option]
    Bot: Select a squadron by number or type 'maintenance':
    User: maintenance
    """
    # Fetch and display aircraft types
    aircraft_types = fetch_aircraft_types(DB_PATH)
    embed = discord.Embed(title="Aircraft Types", description="Select an aircraft type by number:", color=0x00ff00)
    for i, aircraft_type in enumerate(aircraft_types, start=1):
        embed.add_field(name=f"{i}.", value=aircraft_type, inline=False)
    await ctx.send(embed=embed)

    # Get user response for aircraft type
    type_response = await get_response(ctx)
    if type_response is None:
        return

    try:
        selected_type_index = int(type_response) - 1
        selected_type = aircraft_types[selected_type_index]
    except (ValueError, IndexError):
        await ctx.send("Invalid selection. Please respond with a valid number.")
        return

    await ctx.send(f"You selected: {selected_type}")

    # List aircraft IDs for selected type
    aircraft_ids = fetch_aircraft_ids_by_type(DB_PATH, selected_type)
    if not aircraft_ids:
        await ctx.send(f"No aircraft found for type {selected_type}.")
        return

    aircraft_embed = discord.Embed(title=f"Aircraft IDs for {selected_type}", description="Select aircraft ID(s) by typing them separated by commas:", color=0x00ff00)
    aircraft_embed.add_field(name="Available Aircraft", value="\n".join(aircraft_ids), inline=False)
    await ctx.send(embed=aircraft_embed)

    # Get user response for aircraft IDs
    aircraft_response = await get_response(ctx)
    if aircraft_response is None:
        return

    selected_aircraft_ids = [aid.strip() for aid in aircraft_response.split(',')]
    if any(aid not in aircraft_ids for aid in selected_aircraft_ids):
        await ctx.send("Invalid aircraft IDs. Please select valid IDs.")
        return

    # List squadrons for selected aircraft type
    squadrons = fetch_squadrons_for_type(DB_PATH, selected_type)
    if not squadrons:
        await ctx.send(f"No squadrons found for aircraft type {selected_type}.")
        return

    squadron_embed = discord.Embed(title="Squadrons", description="Select a squadron by number or type 'maintenance' to send to maintenance:", color=0x00ff00)
    for i, squadron in enumerate(squadrons, start=1):
        squadron_embed.add_field(name=f"{i}.", value=squadron, inline=False)
    await ctx.send(embed=squadron_embed)

    # Get user response for squadron selection
    squadron_response = await get_response(ctx)
    if squadron_response is None:  # User did not respond
        return

    if squadron_response.lower() == 'maintenance':
        send_aircraft_to_maintenance(DB_PATH, selected_aircraft_ids)
        await ctx.send(f"Aircraft {', '.join(selected_aircraft_ids)} sent to maintenance.")
    else:
        try:
            selected_squadron_index = int(squadron_response) - 1
            if selected_squadron_index < 0 or selected_squadron_index >= len(squadrons):
                raise IndexError
            selected_squadron_id = squadrons[selected_squadron_index]  # Get the actual squadron_id
        except (ValueError, IndexError):
            await ctx.send("Invalid selection. Please respond with a valid number.")
            return

        assign_aircraft_to_squadron(DB_PATH, selected_squadron_id, selected_aircraft_ids)
        await ctx.send(f"Aircraft {', '.join(selected_aircraft_ids)} assigned to squadron {selected_squadron_id}.")

@bot.command(name='update_mayfly')
async def update_mayfly(ctx):
    """
    Updates the state, ETBOL, and remarks for selected aircraft.
    This command prompts the user to enter aircraft IDs, then provides options to update
    the aircraft state, ETBOL, and remarks for those aircraft.
    
    It will also take the number of hours to add to the current time for ETBOL.
    
    Usage: !update_mayfly
    """
    # Ask the user to enter the aircraft IDs directly
    await ctx.send("Enter aircraft ID(s) (comma-separated):")
    aircraft_response = await get_response(ctx)
    if aircraft_response is None:
        return

    # Clean up and validate the aircraft IDs entered by the user
    selected_aircraft_ids = [aid.strip() for aid in aircraft_response.split(',')]
    if not selected_aircraft_ids:
        await ctx.send("No aircraft IDs provided. Please try again.")
        return

    # Prompt for new state
    await ctx.send("Enter new state for the aircraft ('S' for Serviceable, 'US' for Unserviceable):")
    state_response = await get_response(ctx)
    if state_response is None:
        return

    if state_response not in ['S', 'US']:
        await ctx.send("Invalid state. Please enter 'S' for Serviceable or 'US' for Unserviceable.")
        return

    # Prompt for ETBOL in hours (expected time before offloading)
    await ctx.send("Enter new ETBOL in hours (to be added to the current time):")
    etbol_response = await get_response(ctx)
    if etbol_response is None:
        return

    try:
        hours_to_add = int(etbol_response)
        new_etbol_time = datetime.datetime.now() + timedelta(hours=hours_to_add)
        etbol_epoch = int(new_etbol_time.timestamp())  # Convert to epoch time
    except ValueError:
        await ctx.send("Invalid ETBOL. Please enter a valid number of hours.")
        return

    # Prompt for remarks
    await ctx.send("Enter remarks for the aircraft:")
    remarks_response = await get_response(ctx)
    if remarks_response is None:
        return

    # Prepare updates for each selected aircraft
    aircraft_updates = []
    for aircraft_id in selected_aircraft_ids:
        aircraft_updates.append({
            'aircraft_id': aircraft_id,
            'aircraft_state': state_response,
            'aircraft_etbol': etbol_epoch,  # Store the new ETBOL time as an epoch
            'aircraft_remarks': remarks_response
        })

    # Update the database with the new values
    update_aircraft_state(DB_PATH, aircraft_updates)

    # Confirmation message
    await ctx.send(f"Aircraft {', '.join(selected_aircraft_ids)} updated.")

    if update_mayfly_html():
        await ctx.send("Mayfly HTML updated successfully!")
    else:
        await ctx.send("Failed to update Mayfly HTML.")

@bot.command(name='submit_stores_request')
async def submit_stores_request(ctx):
    """
    Allows users to submit a stores request by collecting necessary details through direct messages (DMs).

    This command facilitates the filing of a stores request by prompting the user to provide various details
    such as receiving unit, receiving magazine location, need-by date, stores requested, and additional details.
    The process is carried out through DMs for privacy and ease of data collection.

    Usage: !submit_stores_request
    """

    # Helper function to prompt for input and return response in DMs
    async def prompt_and_get_response_dm(prompt):
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send(prompt)
        response = await get_response_dm(ctx, dm_channel)
        return response if response else None

    # Function to wait for user's response in DMs
    async def get_response_dm(ctx, dm_channel):
        def check(m):
            return m.author == ctx.author and m.channel == dm_channel

        try:
            response = await bot.wait_for('message', check=check, timeout=90.0)
            return response.content
        except asyncio.TimeoutError:
            await dm_channel.send("You did not respond in time.")
            return None

    # Inform user that the interaction will continue in DMs
    await ctx.send(f"{ctx.author.mention}, please check your DMs to submit the stores request.")

    # Collecting all necessary inputs from the user
    receiving_unit = await prompt_and_get_response_dm("Please enter the receiving unit:")
    if not receiving_unit:
        return

    receiving_magazine_location = await prompt_and_get_response_dm("Please enter the receiving magazine location:")
    if not receiving_magazine_location:
        return

    need_by_date = await prompt_and_get_response_dm("Please enter the need-by date (e.g., 2024-10-20):")
    if not need_by_date:
        return

    stores_requested = await prompt_and_get_response_dm("Please enter the stores requested (e.g., 10x AGM-65, 50x 120mm rounds):")
    if not stores_requested:
        return

    additional_details = await prompt_and_get_response_dm("Please enter additional details (e.g., operation or mission details) (optional, press Enter to skip):")

    # Use ctx.author.name to get the requester's Discord name
    requester = str(ctx.author)

    # Use the current date for the request
    request_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Insert data into the database
    insert_success = insert_stores_request(DB_PATH, requester, request_date, receiving_unit, receiving_magazine_location, need_by_date, stores_requested, additional_details)

    if insert_success:
        # Send a confirmation message
        embed = discord.Embed(title="JSW Stores Request System", color=0x2ecc71)
        embed.add_field(name="Requester", value=requester, inline=True)
        embed.add_field(name="Date", value=request_date, inline=True)
        embed.add_field(name="Receiving Unit", value=receiving_unit, inline=True)
        embed.add_field(name="Receiving Magazine Location", value=receiving_magazine_location, inline=True)
        embed.add_field(name="Need By Date", value=need_by_date, inline=True)
        embed.add_field(name="Stores Requested", value=stores_requested, inline=False)
        embed.add_field(name="Additional Details", value=additional_details or "N/A", inline=False)

        embed.set_footer(text="Stores Request Submitted Successfully")

        # Send confirmation to the user in DMs
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send(embed=embed)

        # Now send the report to the relevant channel (if applicable)
        target_channel_name = STORES_REQUEST_CHANNEL_NAME  # Update with the correct channel name
        target_channel = None
        for channel in ctx.guild.channels:
            if channel.name == target_channel_name:
                target_channel = channel
                break

        # Specify the role you want to mention (by ID)
        role_id = int(STORES_OFFICER_ROLE)  # Update with the correct role ID
        role_to_mention = ctx.guild.get_role(role_id)

        # Send the report to the stores request channel
        if target_channel and role_to_mention:
            await target_channel.send(content=f"{role_to_mention.mention}", embed=embed)
        else:
            await ctx.send("Target channel or role not found.")
    else:
        # Handle the failure to insert a new stores request
        await ctx.send("Failed to submit the stores request.")

@bot.command(name='submit_expenditure_report')
async def submit_expenditure_report(ctx):
    """
    Allows users to submit an expenditure report by collecting necessary details through direct messages (DMs).

    This command facilitates the filing of an expenditure report by prompting the user to provide various details
    such as the operation name, squadron, stores used, and optionally a battle damage assessment (BDA) and after-action report (AAR).
    The process is carried out through DMs for privacy and ease of data collection.

    Usage: !submit_expenditure_report
    """

    # Helper function to prompt for input and return response in DMs
    async def prompt_and_get_response_dm(prompt):
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send(prompt)
        response = await get_response_dm(ctx, dm_channel)
        return response if response else None

    # Function to wait for user's response in DMs
    async def get_response_dm(ctx, dm_channel):
        def check(m):
            return m.author == ctx.author and m.channel == dm_channel

        try:
            response = await bot.wait_for('message', check=check, timeout=90.0)
            return response.content
        except asyncio.TimeoutError:
            await dm_channel.send("You did not respond in time.")
            return None

    # Inform user that the interaction will continue in DMs
    await ctx.send(f"{ctx.author.mention}, please check your DMs to submit the expenditure report.")

    # Collecting all necessary inputs from the user
    operation_name = await prompt_and_get_response_dm("Please enter the operation/exercise name (e.g., Operation Thunderstrike):")
    if not operation_name:
        return

    squadron = await prompt_and_get_response_dm("Please enter your squadron name:")
    if not squadron:
        return

    stores_used = await prompt_and_get_response_dm("Please enter the stores/weapons used (e.g., 2x AGM-65, 4x AIM-9X):")
    if not stores_used:
        return

    bda = await prompt_and_get_response_dm("Please enter the battle damage assessment (optional, press Enter to skip):")

    aar = await prompt_and_get_response_dm("Please enter the after-action report (optional, press Enter to skip):")

    # Use ctx.author.name to get the reporter's Discord name
    reporter = str(ctx.author)

    # Use the current date for the report
    report_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Insert data into the database
    insert_success = insert_expenditure_report(DB_PATH, reporter, report_date, operation_name, squadron, stores_used, bda, aar)

    if insert_success:
        # Send a confirmation message
        embed = discord.Embed(title="JSW Expenditure Reporting System", color=0x2ecc71)
        embed.add_field(name="Reporter", value=reporter, inline=True)
        embed.add_field(name="Date", value=report_date, inline=True)
        embed.add_field(name="Operation Name", value=operation_name, inline=True)
        embed.add_field(name="Squadron", value=squadron, inline=True)
        embed.add_field(name="Stores Used", value=stores_used, inline=False)
        embed.add_field(name="Battle Damage Assessment", value=bda or "N/A", inline=False)
        embed.add_field(name="After Action Report", value=aar or "N/A", inline=False)

        embed.set_footer(text="Expenditure Report Submitted Successfully")

        # Send confirmation to the user in DMs
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send(embed=embed)

        # Now send the report to the flight plan channel
        target_channel_name = BDA_CHANNEL_NAME
        target_channel = None
        for channel in ctx.guild.channels:
            if channel.name == target_channel_name:
                target_channel = channel
                break

        # Specify the role you want to mention (by ID)
        role_id = int(CO_ROLE)
        role_to_mention = ctx.guild.get_role(role_id)

        # Send the report to the flight plan channel
        if target_channel and role_to_mention:
            await target_channel.send(content=f"{role_to_mention.mention}", embed=embed)
        else:
            await ctx.send("Target channel or role not found.")
    else:
        # Handle the failure to insert a new expenditure report
        await ctx.send("Failed to submit the expenditure report.")

    if update_mayfly_html():
        await ctx.send("Mayfly HTML updated successfully!")
    else:
        await ctx.send("Failed to update Mayfly HTML.")

@bot.command(name='file_flight_plan')
async def file_flight_plan(ctx):
    """
    Files a new flight plan by collecting necessary details through direct messages (DMs).

    This command facilitates the filing of a flight plan by prompting the user to provide various details such as aircraft type, callsign, flight rules, type of flight, departure and destination aerodromes, route, and other relevant information. The process is carried out through DMs for privacy and ease of data collection. Upon successful filing, a confirmation message is sent, and the flight plan details are updated in the database.

    Usage: !file_flight_plan

    Example:
    User: !file_flight_plan
    Bot: [In DMs] Please enter the aircraft type (e.g., FGR1 X2):
    User: [Responds in DMs with each detail as prompted]
    Bot: [In server] Flight Plan Filed Successfully [with detailed embed]
    """
    # Helper function to prompt for input, convert to uppercase, and return response in DMs
    async def prompt_and_get_response_dm(prompt):
        dm_channel = await ctx.author.create_dm()
        await dm_channel.send(prompt)
        response = await get_response_dm(ctx, dm_channel)
        return response.upper() if response else None

    # Function to wait for user's response in DMs
    async def get_response_dm(ctx, dm_channel):
        def check(m):
            return m.author == ctx.author and m.channel == dm_channel

        try:
            response = await bot.wait_for('message', check=check, timeout=90.0)
            return response.content
        except asyncio.TimeoutError:
            await dm_channel.send("You did not respond in time.")
            return None

    # Inform user that the interaction will continue in DMs
    await ctx.send(f"{ctx.author.mention}, please check your DMs to file the flight plan.")

    # Collecting all necessary inputs from the user
    aircraft_type = await prompt_and_get_response_dm("Please enter the aircraft type (e.g., FGR1 X2):")
    if not aircraft_type:
        return

    aircraft_callsign = await prompt_and_get_response_dm("Please enter the aircraft callsign (e.g., CHAOS):")
    if not aircraft_callsign:
        return

    flight_rules = await prompt_and_get_response_dm("Please enter the flight rules (e.g., IFR, VFR):")
    if not flight_rules:
        return

    type_of_flight = await prompt_and_get_response_dm("Please enter the type of flight (e.g., TRAINING, CAP, NAVEX):")
    if not type_of_flight:
        return

    departure_aerodrome = await prompt_and_get_response_dm("Please enter the departure aerodrome (e.g., UGTB):")
    if not departure_aerodrome:
        return

    departure_time = await prompt_and_get_response_dm("Please enter the departure time: (e.g., 130200ZJAN24)")
    if not departure_time:
        return

    route = await prompt_and_get_response_dm("Please enter the route: (e.g., DANGR via B-143)")
    if not route:
        return

    destination_aerodrome = await prompt_and_get_response_dm("Please enter the destination aerodrome: (e.g., UGSB)")
    if not destination_aerodrome:
        return

    total_estimated_elapsed_time = await prompt_and_get_response_dm("Please enter the total estimated elapsed time: (e.g., 90 min)")
    if not total_estimated_elapsed_time:
        return

    alternate_aerodrome = await prompt_and_get_response_dm("Please enter an alternate aerodrome (if any):")

    fuel_on_board = await prompt_and_get_response_dm("Please enter the fuel on board: (e.g., 11000 LBS)")
    if not fuel_on_board:
        return

    other_information = await prompt_and_get_response_dm("Please enter any other information or remarks (e.g., Ordinance onboard or request use of MOAs):")

    # Insert data into the database (assuming function exists in db_crud.py)
    insert_success = insert_flight_plan(DB_PATH, aircraft_type, aircraft_callsign, flight_rules, type_of_flight, departure_aerodrome, departure_time, route, destination_aerodrome, total_estimated_elapsed_time, alternate_aerodrome, fuel_on_board, other_information)

    if insert_success:
        # Generate the updated flights.html page
        generate_flight_plans_page(DB_PATH, 'html/flights.html')  # Adjust the path as needed

        # Send an embedded confirmation message
        embed = discord.Embed(title="JSW Flight Filing System", color=0xd62828)
        embed.add_field(name="Type", value=aircraft_type, inline=True)
        embed.add_field(name="Callsign", value=aircraft_callsign, inline=True)
        embed.add_field(name="Flight Rules", value=flight_rules, inline=True)
    
        embed.add_field(name="Departure Aerodrome and Time", value=f"{departure_aerodrome} {departure_time}", inline=True)
        embed.add_field(name="Route", value=route, inline=False)

        embed.add_field(name="Destination Aerodrome", value=destination_aerodrome, inline=True)
        embed.add_field(name="Total Estimated Elapsed Time", value=total_estimated_elapsed_time, inline=True)

        embed.add_field(name="Alternate Aerodrome", value=alternate_aerodrome or "N/A", inline=True)
        embed.add_field(name="Fuel Onboard", value=fuel_on_board, inline=True)

        embed.add_field(name="Remarks", value=other_information or "None", inline=False)
        embed.set_footer(text="Flight Plan Filed Successfully")

        # Specify the target channel by name
        target_channel_name = CONTROLLERS_CHANNEL_NAME
        target_channel = None
        for channel in ctx.guild.channels:
            logger.info(f"Checking channel: {channel.name}")  # Debugging statement
            if channel.name == target_channel_name:
                target_channel = channel
                break
            
        # Debugging: Check if the channel was found
        if target_channel:
            logger.info(f"Found channel: {target_channel.name}")
        else:
            logger.error("Channel not found.")

        # Specify the role you want to mention (by ID)
        role_id = int(CONTROLLER_ROLE)
        role_to_mention = ctx.guild.get_role(role_id)
        logger.info(f"Looking for role ID: {role_id}.  Corresponsing role name: {role_to_mention}")

        # Debugging: Check if the role was found
        if role_to_mention:
            logger.info(f"Found role: {role_to_mention.name}")
        else:
            logger.error("Role not found.")

        # Send the message to the specified channel and mention the role
        if target_channel and role_to_mention:
            await target_channel.send(content=f"{role_to_mention.mention}", embed=embed)
        else:
            await ctx.send("Target channel or role not found.")

    else:
        # Handle the failure to insert a new flight plan
        await ctx.send("Failed to file the flight plan.")

    if update_mayfly_html():
        await ctx.send("Mayfly HTML updated successfully!")
    else:
        await ctx.send("Failed to update Mayfly HTML.")

# Override the default help command
bot.remove_command('help')

@bot.command(name='help')
async def help_command(ctx, command_name=None):
    """
    Provides help information about commands using embedded messages, sorted alphabetically.

    Usage: !help [command_name]

    Parameters:
    command_name (str, optional): The name of the command to get detailed help for.

    Example:
    !help  # Lists all commands alphabetically
    !help assign_pilot  # Detailed help for assign_pilot command
    """
    if command_name:
        # Detailed help for a specific command
        command = bot.get_command(command_name)
        if command:
            help_text = command.help or 'No detailed help available for this command.'
            embed = discord.Embed(title=f"!{command.name}", description=help_text, color=0x00ff00)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"No command named '{command_name}' found.")
    else:
        # General help - list all commands alphabetically
        embed = discord.Embed(title="Available Commands", description="List of all available commands and their arguments, sorted alphabetically:", color=0x00ff00)
        commands_sorted = sorted(bot.commands, key=lambda cmd: cmd.name)
        for command in commands_sorted:
            # Determine the permission requirement for the command
            permission_info = ""
            if any(check.__qualname__.startswith('is_server_admin') for check in command.checks):
                permission_info = " [Server Admin Only]"
            elif any(check.__qualname__.startswith('is_commanding_officer') for check in command.checks):
                permission_info = " [Commanding Officer Only]"

            # Add command info to the embed
            first_line = command.help.split('\n')[0] if command.help else 'No description available'
            embed.add_field(name=f"!{command.name} {command.signature}{permission_info}", value=first_line, inline=False)
        await ctx.send(embed=embed)

def create_embed(page_content, page_title, page_number):
    embed = discord.Embed(title=page_title, description=f"Page {page_number}", color=0x00ff00)
    
    # Split the page_content to get the category and the list of pilots
    category, pilots = page_content.split(':', 1)
    category = f"**{category}**"  # Make the category bold

    embed.add_field(name=category, value=pilots.strip(), inline=False)
    return embed

@bot.command(name='audit_logbook')
@is_commanding_officer()
async def audit_logbook(ctx):
    report_data = generate_pilot_hour_report(JSON_PATH, DB_PATH)
    report_pages = chunk_report(report_data)  # Assume chunk_report divides report_data into pages

    current_page = 0
    message = await ctx.send(embed=create_embed(report_pages[current_page], "Pilot Hour Audit Report", current_page + 1))
    
    # Add reaction arrows if there are multiple pages
    if len(report_pages) > 1:
        await message.add_reaction('⬅️')
        await message.add_reaction('➡️')

        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id
        
        while True:
            try:
                reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
                if str(reaction.emoji) == '➡️' and current_page < len(report_pages) - 1:
                    current_page += 1
                    await message.edit(embed=create_embed(report_pages[current_page], "Pilot Hour Audit Report", current_page + 1))
                    await message.remove_reaction(reaction, user)
                elif str(reaction.emoji) == '⬅️' and current_page > 0:
                    current_page -= 1
                    await message.edit(embed=create_embed(report_pages[current_page], "Pilot Hour Audit Report", current_page + 1))
                    await message.remove_reaction(reaction, user)
            except asyncio.TimeoutError:
                break

bot.run(TOKEN)