import discord
import asyncio
import logging
from discord.ext import commands
from database.db_crud import find_pilot_id_by_name, assign_pilot_to_squadron, get_squadron_ids
from discord_bot.config import TOKEN

# Configure logging
log_filename = f"data/logs/bot.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

db_path = 'data/db/mayfly.db'
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.command(name='assign_pilot')
async def assign_pilot(ctx, pilot_name):
    logging.info(f"Assigning pilot: {pilot_name}")
    pilot_id = find_pilot_id_by_name(db_path, pilot_name)
    if not pilot_id:
        await ctx.send(f"No pilot found with the name: {pilot_name}")
        logging.warning(f"Pilot not found: {pilot_name}")
        return

    squadrons = get_squadron_ids(db_path)
    squadrons_list = ', '.join(squadrons)
    await ctx.send(f"Available squadrons: {squadrons_list}\nPlease select one or more squadron IDs (separated by commas) for pilot '{pilot_name}':")

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    try:
        response = await bot.wait_for('message', check=check, timeout=60.0)  # 60 seconds to reply
        selected_squadrons = [s.strip() for s in response.content.split(',')]
        for squadron_id in selected_squadrons:
            if squadron_id in squadrons:
                assign_pilot_to_squadron(db_path, pilot_id, squadron_id)
        await ctx.send(f"Pilot '{pilot_name}' assigned to selected squadrons.")
        logging.info(f"Pilot {pilot_name} assigned to squadrons: {selected_squadrons}")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        logging.error(f"Error in assign_pilot: {e}")
    except asyncio.TimeoutError:
        await ctx.send("You did not respond in time.")
        logging.warning("Timeout in assign_pilot command.")

bot.run(TOKEN)
