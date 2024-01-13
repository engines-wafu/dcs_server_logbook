import discord, asyncio, logging, time, datetime, tracemalloc
from main import main
from utils.ribbon import ribbonGenerator, create_award_quilt
from discord.ext import commands
from html_generator.html_generator import generate_index_html, load_combined_stats, generate_flight_plans_page
from utils.stat_processing import get_pilot_qualifications_with_details, get_pilot_awards_with_details, get_pilot_details
from database.db_crud import *
from config import TOKEN, DB_PATH, JSON_PATH

tracemalloc.start()

# Configure logging
log_filename = f"data/logs/bot.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

output_path = 'web/index.html'
json_path = 'data/stats/combinedStats.json'
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
predefined_colors = [
  "#DAA520", 
  "#C0C0C0", 
  "#CD7F32", 
  "#B9CCED", 
  "#800000", 
  "#008000", 
  "#000080", 
  "#FFD700", 
  "#A52A2A", 
  "#FFA500", 
  "#4682B4", 
  "#6B8E23"
]

@bot.command(name='add_squadron')
async def add_squadron(ctx):
    """
    Adds a new squadron to the database, with details collected via direct messages (DMs).

    This command guides the user through the process of adding a new squadron by prompting for necessary information such as squadron ID, motto, service branch, commission date, commanding officer, aircraft type, and pseudo type. The process is conducted through DMs for privacy. Once all details are provided, the new squadron is added to the database, and a confirmation is sent in an embedded message format.

    Usage: !add_squadron

    Example:
    User: !add_squadron
    Bot: [In DMs] Please enter the squadron ID:
    User: [Responds in DMs with each detail as prompted]
    Bot: [In server] Squadron Added Successfully [with detailed embed]
    """
    # Helper function to prompt for input in DMs and return response
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

    # Collecting squadron details from the user
    logging.info("Starting to collect squadron details via DMs.")
    squadron_id = await prompt_and_get_response_dm("Please enter the squadron ID:")
    if not squadron_id:
        logging.warning("Squadron ID not provided. Exiting command.")
        return

    squadron_motto = await prompt_and_get_response_dm("Please enter the squadron motto:")
    squadron_service = await prompt_and_get_response_dm("Please enter the squadron service branch (e.g., RN, Army, RAF):")
    squadron_commission_date_str = await prompt_and_get_response_dm("Please enter the squadron commission date (YYYY-MM-DD):")
    if not squadron_commission_date_str:
        return
    squadron_commanding_officer = await prompt_and_get_response_dm("Please enter the name of the commanding officer:")
    squadron_aircraft_type = await prompt_and_get_response_dm("Please enter the squadron aircraft type:")
    squadron_pseudo_type = await prompt_and_get_response_dm("Please enter the squadron pseudo type:")

    # Validate squadron_service
    valid_services = ['RN', 'Army', 'RAF']
    if squadron_service not in valid_services:
        await ctx.send(f"Invalid service branch. Please choose from {valid_services}.")
        return

    # Convert the date string to epoch time
    try:
        commission_date_obj = datetime.datetime.strptime(squadron_commission_date_str, "%Y-%m-%d")
        squadron_commission_date = int(commission_date_obj.timestamp())
    except ValueError:
        await ctx.send("Invalid date format. Please use YYYY-MM-DD.")
        return

    logging.info("Starting the !add_squadron command.")
    try:
        # Run the add_squadron function in an executor to avoid blocking
        loop = asyncio.get_event_loop()
        insert_success = await loop.run_in_executor(None, add_squadron, 
            DB_PATH, squadron_id, squadron_motto, squadron_service,
            squadron_commission_date, squadron_commanding_officer,
            squadron_aircraft_type, squadron_pseudo_type)

        if insert_success:
            logging.info(f"Squadron {squadron_id} added successfully to the database.")
            # Sending confirmation message with embedded format
            # [Construct and send the embedded message as before]
        else:
            logging.warning(f"Failed to add Squadron {squadron_id} to the database.")
            await ctx.send("Failed to add the squadron.")
    except Exception as e:
        logging.exception("Exception occurred in !add_squadron command: ", exc_info=e)
        await ctx.send("An error occurred while processing the command.")

def generate_single_ribbon(award_name, file_path, min_block_width_percent=10, max_block_width_percent=30):
    pattern_generator = ribbonGenerator(
        award_name,
        color_array=predefined_colors,
        min_block_width_percent=min_block_width_percent,
        max_block_width_percent=max_block_width_percent
    )
    pattern_generator.save_pattern_as_png(file_path)

async def get_response(ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=90.0)
        return response.content
    except asyncio.TimeoutError:
        await ctx.send("You did not respond in time.")
        return None

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
    pilot_name = get_pilot_name(DB_PATH, pilot_id)

    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return

    # Load combined stats from the JSON file
    combined_stats = load_combined_stats(JSON_PATH)  # Ensure that JSON_PATH is correctly defined and accessible

    pilot_details = get_pilot_details(DB_PATH, pilot_id, combined_stats)
    if not pilot_details:
        await ctx.send(f"No details found for pilot: {pilot_name}")
        return

    # Generate ribbon quilt image
    create_award_quilt(DB_PATH, pilot_id)  # This will create the image at 'web/img/fruit_salad/[pilot_id].png'

    # Prepare the image file to be sent
    image_path = f'web/img/fruit_salad/{pilot_id}.png'
    image_file = discord.File(image_path, filename='fruit_salad.png')

    # Construct the embedded message with pilot details
    embed = discord.Embed(title=f"Pilot Information: {pilot_name}", color=0x00ff00)
    embed.add_field(name="Service", value=pilot_details['service'], inline=True)
    embed.add_field(name="Rank", value=pilot_details['rank'], inline=True)
    embed.add_field(name="Total Hours", value=str(pilot_details['total_hours']), inline=True)
    embed.add_field(name="Last Joined", value=pilot_details['last_join'], inline=True)

    # Add qualifications and awards to the embed
    qualifications = get_pilot_qualifications_with_details(DB_PATH, pilot_id)
    awards = get_pilot_awards_with_details(DB_PATH, pilot_id)
    
    # Add qualifications to embed
    if qualifications:
        qualifications_text = "\n".join(f"{q[1]} (Issued: {q[3]}, Expires: {q[4]})" for q in qualifications)
        embed.add_field(name="Qualifications", value=qualifications_text, inline=False)
    else:
        embed.add_field(name="Qualifications", value="None", inline=False)

    # Add awards to embed
    if awards:
        awards_text = "\n".join(f"{a[1]} (Issued: {a[3]})" for a in awards)
        embed.add_field(name="Awards", value=awards_text, inline=False)
    else:
        embed.add_field(name="Awards", value="None", inline=False)

    # Attach the image to the embed
    embed.set_image(url="attachment://fruit_salad.png")

    # Send the embed with the image
    await ctx.send(file=image_file, embed=embed)

@bot.command(name='update_logbook')
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
        main()  # Call the main function from main.py
        await ctx.send("Logbook updated successfully.")
    except Exception as e:
        await ctx.send(f"An error occurred while updating the logbook: {e}")

@bot.command(name='create_award')
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
        ribbon_path = 'web/img/ribbons/' + award_name.replace(" ", "_") + '.png'
        # Here you can also pass different min and max width percentages if needed
        generate_single_ribbon(award_name, ribbon_path)
        await ctx.send(f"Ribbon for '{award_name}' created successfully.")
    except Exception as e:
        await ctx.send(f"Failed to create ribbon: {e}")
    
@bot.command(name='create_qualification')
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
async def give_award(ctx):
    """
    Assigns specified awards to selected pilots.
    
    This command first displays a list of available awards. The user is then prompted to enter the names of the pilots (comma-separated) and the IDs of the awards (also comma-separated). The specified awards are then assigned to the given pilots.
    
    Usage: !give_award

    Example:
    User: !give_award
    Bot: [Displays list of available awards]
    Bot: Enter pilot name(s) (comma-separated):
    User: JohnDoe, JaneDoe
    Bot: Enter the award ID(s) from the list above (comma-separated):
    User: 1, 3
    """
    # Retrieve available awards
    awards = get_awards(DB_PATH)
    if not awards:
        await ctx.send(embed=discord.Embed(description="No awards available.", color=0xff0000))
        return

    # Create an embed for awards
    embed = discord.Embed(title="Available Awards", description="Select an award by its ID.", color=0x00ff00)
    awards_dict = {str(aid): aname for aid, aname in awards}
    for aid, aname in awards_dict.items():
        embed.add_field(name=aid, value=aname, inline=False)

    # Send award list and ask for pilot name(s)
    award_msg = await ctx.send(embed=embed)
    await ctx.send("Enter pilot name(s) (comma-separated):")
    pilot_names_response = await get_response(ctx)
    if not pilot_names_response:
        return

    pilot_ids = [find_pilot_id_by_name(DB_PATH, name.strip()) for name in pilot_names_response.split(",") if name.strip()]

    # Prompt for award selection
    await ctx.send("Enter the award ID(s) from the list above (comma-separated):")
    award_ids_response = await get_response(ctx)
    if not award_ids_response:
        return

    award_ids = award_ids_response.split(",")

    # Assign award to pilots
    for pilot_id in pilot_ids:
        for award_id in award_ids:
            if award_id.strip() in awards_dict:
                assign_award_to_pilot(DB_PATH, pilot_id, int(award_id.strip()))

    await ctx.send(embed=discord.Embed(description="Award(s) assigned to selected pilot(s).", color=0x00ff00))

@bot.command(name='give_qualification')
async def give_qualification(ctx):
    """
    Assigns specified qualifications to selected pilots.

    This command first displays a list of available qualifications. The user is then prompted to enter the names of the pilots (comma-separated) and the ID of the qualification. The specified qualification is then assigned to the given pilots, along with its duration.

    Usage: !give_qualification

    Example:
    User: !give_qualification
    Bot: [Displays list of available qualifications]
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

    # Create an embed for qualifications
    embed = discord.Embed(title="Available Qualifications", description="Select a qualification by its ID.", color=0x00ff00)
    for qid, qname, _ in qualifications:
        embed.add_field(name=qid, value=qname, inline=False)

    # Send qualification list and ask for pilot name(s)
    qualification_msg = await ctx.send(embed=embed)
    await ctx.send("Enter pilot name(s) (comma-separated):")
    pilot_names = await get_response(ctx)
    if not pilot_names:
        return

    pilot_ids = [find_pilot_id_by_name(DB_PATH, name.strip()) for name in pilot_names.split(",")]

    # Prompt for qualification selection
    await ctx.send("Enter the qualification ID from the list above:")
    qualification_id = await get_response(ctx)
    if not qualification_id:
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
        generate_flight_plans_page(DB_PATH, 'web/flights.html')  # Adjust the path as needed

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
        target_channel_name = 'controllers'
        target_channel = None
        for channel in ctx.guild.channels:
            if channel.name == target_channel_name:
                target_channel = channel
                break

        # Specify the role you want to mention (by ID)
        role_id = 1195557831223545888 # Replace with the actual role ID
        role_to_mention = ctx.guild.get_role(role_id)

        # Send the message to the specified channel and mention the role
        if target_channel and role_to_mention:
            await target_channel.send(content=f"{role_to_mention.mention}", embed=embed)
        else:
            await ctx.send("Target channel or role not found.")
            # ... [code to send the embed message] ...
    else:
        # Handle the failure to insert a new flight plan
        await ctx.send("Failed to file the flight plan.")

# Override the default help command
bot.remove_command('help')

@bot.command(name='help')
async def help_command(ctx, command_name=None):
    """
    Provides help information about commands using embedded messages, with headlines from docstrings.

    Usage: !help [command_name]

    Parameters:
    command_name (str, optional): The name of the command to get detailed help for.

    Example:
    !help  # Lists all commands with headlines from docstrings
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
        # General help - list all commands with embedded format
        embed = discord.Embed(title="Available Commands", description="List of all available commands and their arguments:", color=0x00ff00)
        for command in bot.commands:
            # Extract the first line (headline) from the command's docstring
            first_line = command.help.split('\n')[0] if command.help else 'No description available'
            embed.add_field(name=f"!{command.name} {command.signature}", value=first_line, inline=False)
        await ctx.send(embed=embed)

bot.run(TOKEN)