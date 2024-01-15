import logging, os, discord
from fuzzywuzzy import process

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

def find_closest_discord_user(pilot_name, pilot_rank, guild_members):
    search_query = f"{pilot_rank} {pilot_name}"
    # Create a list of member names and IDs
    member_names = [member.display_name for member in guild_members]
    member_mapping = {member.display_name: member.id for member in guild_members}

    # Find the closest match
    closest_match, score = process.extractOne(search_query, member_names)

    # Set a threshold for match quality, e.g., 80
    if score > 80:
        return member_mapping[closest_match]
    else:
        return None

async def assign_role(ctx, pilot_name, pilot_rank, role_id):
    logger.debug(f"Attempting to assign role ID {role_id} to pilot: {pilot_rank} {pilot_name}")
    
    guild = ctx.guild
    logger.debug(f"Guild ID: {guild.id}, Guild Name: {guild.name}")

    # Log all roles in the guild
    for role in guild.roles:
        logger.debug(f"Role ID: {role.id}, Role Name: {role.name}")

    # Find the role in the guild by ID
    role = discord.utils.get(guild.roles, id=int(role_id))
    if role is None:
        logger.warning(f"Role with ID {role_id} not found in guild.")
        return

    # Find the member in the guild
    member = discord.utils.get(guild.members, display_name=pilot_name)
    if member is None:
        logger.warning(f"Member with name {pilot_name} not found in guild.")
        return

    # Assign the role
    try:
        await member.add_roles(role)
        logger.info(f"Assigned role {role.name} to user {member.display_name}")
    except Exception as e:
        logger.error(f"Error assigning role: {e}")
