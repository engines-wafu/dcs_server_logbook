import discord
import asyncio
import logging
from discord.ext import commands
from html_generator.html_generator import generate_index_html
from database.db_crud import find_pilot_id_by_name, assign_pilot_to_squadron, get_squadron_ids, get_pilot_name
from discord_bot.config import TOKEN

# Configure logging
log_filename = f"data/logs/bot.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

output_path = 'web/index.html'
db_path = 'data/db/mayfly.db'
json_path = 'data/stats/combinedStats.json'
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.command(name='assign_pilot')
async def assign_pilot(ctx, *, pilot_names):  # Use '*' to capture all text after the command
    pilot_names = [name.strip() for name in pilot_names.split(',')]  # Split and strip pilot names

    pilot_ids = []
    for name in pilot_names:
        pilot_id = find_pilot_id_by_name(db_path, name)
        if pilot_id:
            pilot_ids.append((name, pilot_id))
        else:
            await ctx.send(f"No pilot found with the name: {name}")

    if not pilot_ids:
        return  # Exit if no valid pilots were found

    squadrons = get_squadron_ids(db_path)
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
            name = get_pilot_name(db_path, pilot_id)
            for squadron_id in selected_squadrons:
                assign_pilot_to_squadron(db_path, pilot_id, squadron_id)
            await ctx.send(f"Pilot '{name}' assigned to selected squadrons: {', '.join(selected_squadrons)}.")

    except ValueError:
        await ctx.send("Invalid selection. Please enter valid numbers.")
    except asyncio.TimeoutError:
        await ctx.send("You did not respond in time.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
    
    generate_index_html(db_path, output_path, json_path)
    logging.info("Created index.html output")

bot.run(TOKEN)
