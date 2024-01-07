import discord
import asyncio
import logging
from main import main
from discord.ext import commands
from html_generator.html_generator import generate_index_html
from database.db_crud import *
from config import TOKEN, DB_PATH

# Configure logging
log_filename = f"data/logs/bot.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

output_path = 'web/index.html'
json_path = 'data/stats/combinedStats.json'
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

async def get_response(ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=60.0)
        return response.content
    except asyncio.TimeoutError:
        await ctx.send("You did not respond in time.")
        return None

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
    
bot.run(TOKEN)
