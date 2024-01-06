import logging
import subprocess
import json
from datetime import datetime

# Configure logging
log_filename = f"data/logs/mayfly.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def run_lua_script(script_path, stats_files):
    command = ['lua', script_path] + stats_files
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            logging.error(f"Error running Lua script: {result.stderr}")
            return None
        return result.stdout
    except Exception as e:
        logging.exception(f"An error occurred while running the Lua script: {e}")
        return None

def process_combined_data(combined_data_json):
    try:
        combined_data = json.loads(combined_data_json)
        # Process combined data...
        # Placeholder for processing logic
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON data: {e}")

def process_combined_data(combined_data_json):
    if not combined_data_json:
        print("No data received from the Lua script.")
        return

    try:
        combined_data = json.loads(combined_data_json)
        # Process combined data...
        # Placeholder for processing logic
    except json.JSONDecodeError as e:
        print("Error parsing JSON data:", e)
        print("Received data:", combined_data_json)

# In main function, call process_combined_data after running Lua script

def main():
    lua_script_path = 'src/lua/merge.lua'
    stats_files = [
        'data/stats/SlmodStats_server1.lua', 
        'data/stats/SlmodStats_server2.lua',
        # Add more files as needed
    ]

    logging.info("Running merge.lua script")
    combined_data_json = run_lua_script(lua_script_path, stats_files)

    if combined_data_json:
        logging.info("Processing combined data")
        process_combined_data(combined_data_json)
    else:
        logging.error("No data returned from Lua script")
    
    combined_data_json = 'data/stats/combined_data.json'
    process_combined_data(combined_data_json)

if __name__ == "__main__":
    main()
