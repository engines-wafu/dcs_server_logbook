import logging
import subprocess
import json
from datetime import datetime
from html_generator.html_generator import fetch_squadron_pilots, generate_index_html
from utils.stat_processing import load_combined_stats, generate_pilot_info_page

# Configure logging
log_filename = f"data/logs/mayfly.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def run_lua_script(script_path, stats_files):
    command = ['lua', script_path] + stats_files
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Error running Lua script: {result.stderr}")
        return None
    return result.stdout.strip()  # This should now be the path to the JSON file

def process_combined_data(combined_data_json):
    try:
        combined_data = json.loads(combined_data_json)
        # Process combined data...
        # Placeholder for processing logic
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON data: {e}")

def process_combined_data(file_path):
    try:
        with open(file_path, 'r') as file:
            data = file.read()

        # Print the first 500 characters of the file for debugging
        # print("First 500 characters of the file:", data[:500])

        combined_data = json.loads(data)
        # Process combined data...
        # Placeholder for processing logic

    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON data: {e}")
    except Exception as e:
        logging.error(f"Error reading file: {e}")



def main():
    lua_script_path = 'src/lua/merge.lua'
    stats_files = [
        'data/stats/SlmodStats_server1.lua', 
        'data/stats/SlmodStats_server2.lua',
        # Add more files as needed
    ]
    json_path = 'data/stats/combinedStats.json'
    json_file_path = run_lua_script(lua_script_path, stats_files)
    combined_stats = load_combined_stats(json_file_path)
    output_dir = 'web/pilot'

    logging.info("Running merge.lua script")
    if json_file_path:
        logging.info("Processing combined data")
        process_combined_data(json_file_path)
    else:
        logging.error("No data returned from Lua script")

    combined_data_json = 'data/stats/combinedStats.json'
    process_combined_data(combined_data_json)

    db_path = 'data/db/mayfly.db'
    output_path = 'web/index.html'

    generate_index_html(db_path, output_path, json_path)
    logging.info("Created index.html output")

    logging.info("Generating pilot pages")
    for pilot_id in combined_stats.keys():
        generate_pilot_info_page(db_path, combined_stats, output_dir)

if __name__ == "__main__":
    main()
