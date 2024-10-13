import logging
import os
import subprocess
import json
from datetime import datetime
from html_generator.html_generator import *
from utils.stat_processing import *
from config import *

# Configure logging
log_filename = "data/logs/mayfly.log"
logging.basicConfig(filename=log_filename, level=logging.ERROR, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def run_lua_script(script_path):
    command = ['lua54', script_path]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Error running Lua script: {result.stderr}")
        return None
    return result.stdout.strip()  # This should now be the path to the JSON file

def update_logbook_report():
    logging.info("Combining stats files.")
    combine_pilot_stats_and_output(STATS_FILES, JSON_PATH)

    if os.path.exists(JSON_PATH):
        logging.info("Processing combined data")
        combined_stats = load_combined_stats(JSON_PATH)
    else:
        logging.error("combinedStats.json not found or merge.lua script failed")

    generate_index_html(DB_PATH, 'html/index.html', JSON_PATH)
    generate_mayfly_html(DB_PATH, 'html/mayfly.html')
    generate_awards_qualifications_page(DB_PATH, 'html/awards.html')
    generate_flight_plans_page(DB_PATH, 'html/flights.html')

    # Call the function to generate the simplified training HTML
    generate_qualification_html(DB_PATH, 'html/training.html')

    logging.info("Generating pilot pages")
    output_dir = 'html/pilot'

    for pilot_id in combined_stats.keys():
        pilot_specific_stats = combined_stats.get(pilot_id)
        if pilot_specific_stats:
            generate_pilot_info_page(DB_PATH, pilot_id, pilot_specific_stats, output_dir)

if __name__ == "__main__":
    update_logbook_report()
