import discord, asyncio, logging, time
from main import main
from utils.ribbon import ribbonGenerator
from discord.ext import commands
from html_generator.html_generator import generate_index_html, load_combined_stats
from utils.stat_processing import get_pilot_qualifications_with_details, get_pilot_awards_with_details, get_pilot_details
from database.db_crud import *
from config import TOKEN, DB_PATH, JSON_PATH

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
    pilot_id = find_pilot_id_by_name(DB_PATH, pilot_name)

    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        return

    # Load combined stats from the JSON file
    combined_stats = load_combined_stats(JSON_PATH)  # Ensure that JSON_PATH is correctly defined and accessible

    pilot_details = get_pilot_details(DB_PATH, pilot_id, combined_stats)
    if not pilot_details:
        await ctx.send(f"No details found for pilot: {pilot_name}")
        return

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

    await ctx.send(embed=embed)

@bot.command(name='update_logbook')
async def update_logbook(ctx):
    try:
        await ctx.send("Updating logbook, please wait...")
        main()  # Call the main function from main.py
        await ctx.send("Logbook updated successfully.")
    except Exception as e:
        await ctx.send(f"An error occurred while updating the logbook: {e}")

@bot.command(name='create_award')
async def create_award(ctx):
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



bot.run(TOKEN)