import logging
import os
import subprocess
import json
from datetime import datetime
from html_generator.html_generator import fetch_squadron_pilots, generate_index_html, generate_awards_qualifications_page, generate_flight_plans_page, generate_flight_plans_page
from utils.stat_processing import load_combined_stats, generate_pilot_info_page
from config import DB_PATH, JSON_PATH, STATS_FILES

# Configure logging
log_filename = f"data/logs/mayfly.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')


def run_lua_script(script_path):
    command = ['lua54', script_path]
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

        combined_data = json.loads(data)
        # Process combined data...
        # Placeholder for processing logic

    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON data: {e}")
    except Exception as e:
        logging.error(f"Error reading file: {e}")

def main():
    lua_script_path = 'src/lua/merge.lua'

    logging.info("Running merge.lua script")
    run_lua_script(lua_script_path)

    if os.path.exists(JSON_PATH):
        logging.info("Processing combined data")
        combined_stats = load_combined_stats(JSON_PATH)
        process_combined_data(JSON_PATH)
        # Further processing...
    else:
        logging.error("combinedStats.json not found or merge.lua script failed")

    generate_index_html(DB_PATH, 'web/index.html', JSON_PATH)
    generate_awards_qualifications_page(DB_PATH, 'web/awards.html')

    generate_flight_plans_page(DB_PATH, 'web/flights.html')
    logging.info("Created html output")

    logging.info("Generating pilot pages")
    output_dir = 'web/pilot'

    for pilot_id in combined_stats.keys():
        pilot_specific_stats = combined_stats.get(pilot_id)
        if pilot_specific_stats:
            generate_pilot_info_page(DB_PATH, pilot_id, pilot_specific_stats, output_dir)

if __name__ == "__main__":
    main()
