import json, re, logging, os
import pandas as pd

# Get the absolute path of the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
project_root = os.path.dirname(project_root)
print(f"Project root is: {project_root}")

# Log file path
log_filename = os.path.join(project_root, "data/logs/stats.log")

# Ensure the log directory exists
os.makedirs(os.path.dirname(log_filename), exist_ok=True)

# Configure a separate logger for your bot
logger = logging.getLogger('stats_processor')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(filename=log_filename)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def json_integrity_check(file_path):
    # Regex pattern for 32-character hex hash
    regex_pattern = r'[0-9a-f]{32}'

    # Read the entire file as a string
    with open(file_path, 'r') as file:
        file_content = file.read()

    # Count occurrences of the pattern in the file
    matches = re.findall(regex_pattern, file_content)
    num_regex_matches = len(set(matches))
    logger.info(f"Number of regex matches: {num_regex_matches}")

    # Load the JSON file and count the number of unique pilot IDs
    with open(file_path, 'r') as file:
        data = json.load(file)

    unique_pilot_ids = set(data.keys())
    unique_pilot_ids.discard("host")  # Disregard the "host" value
    num_unique_pilot_ids = len(unique_pilot_ids)
    logger.info(f"Number of unique pilot IDs in JSON (excluding 'host'): {num_unique_pilot_ids}")

    # Check for discrepancies
    if num_regex_matches == num_unique_pilot_ids:
        logger.info("JSON integrity check passed: No discrepancies found.")
        return True
    else:
        missing_in_regex = unique_pilot_ids - set(matches)
        missing_in_json = set(matches) - unique_pilot_ids
        logger.error("JSON integrity check failed: Discrepancies found.")
        logger.error(f"Pilot IDs in JSON but not in regex matches: {missing_in_regex}")
        logger.error(f"Pilot IDs in regex matches but not in JSON: {missing_in_json}")
        return False

def print_pilot_total_times(file_path):
    # Load the JSON file
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Iterate over each pilot and calculate their total time
    for pilot_id, stats in data.items():
        if pilot_id == "host":
            continue  # Skip the "host" entry

        total_seconds = 0
        if 'times' in stats:
            for aircraft, aircraft_stats in stats['times'].items():
                total_seconds += aircraft_stats.get('total', 0)

        total_hours = round(total_seconds / 3600, 1)
        print(f"Pilot ID: {pilot_id}, Total Hours: {total_hours}")

def combine_pilot_total_times(file_paths):
    # Check the integrity of each file
    for file_path in file_paths:
        if not json_integrity_check(file_path):
            logging.error(f"Integrity check failed for file: {file_path}")
            return

    # Dictionary to store combined total times for each pilot
    combined_totals = {}

    # Process each file
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            data = json.load(file)

        for pilot_id, stats in data.items():
            if pilot_id == "host":
                continue  # Skip the "host" entry

            total_seconds = 0
            if 'times' in stats:
                for aircraft, aircraft_stats in stats['times'].items():
                    total_seconds += aircraft_stats.get('total', 0)

            if pilot_id in combined_totals:
                combined_totals[pilot_id] += total_seconds
            else:
                combined_totals[pilot_id] = total_seconds

    # Print the combined total times for each pilot
    for pilot_id, total_seconds in combined_totals.items():
        total_hours = round(total_seconds / 3600, 1)
        print(f"Pilot ID: {pilot_id}, Combined Total Hours: {total_hours}")

def combine_pilot_stats_and_output(file_paths, output_file_path):
    combined_stats = {}

    # Function to update the combined stats with data from a file
    def update_combined_stats(data):
        for pilot_id, stats in data.items():
            if pilot_id == "host":
                continue  # Skip the "host" entry

            if pilot_id not in combined_stats:
                combined_stats[pilot_id] = {"times": {}, "lastJoin": 0}

            # Update lastJoin
            combined_stats[pilot_id]["lastJoin"] = max(combined_stats[pilot_id]["lastJoin"], stats.get("lastJoin", 0))

            # Aggregate times and kills for each aircraft
            for aircraft, aircraft_stats in stats.get("times", {}).items():
                if aircraft not in combined_stats[pilot_id]["times"]:
                    combined_stats[pilot_id]["times"][aircraft] = {"total": 0, "inAir": 0}
                combined_stats[pilot_id]["times"][aircraft]["total"] += aircraft_stats.get("total", 0)
                combined_stats[pilot_id]["times"][aircraft]["inAir"] += aircraft_stats.get("inAir", 0)
                if "kills" in aircraft_stats:
                    combined_stats[pilot_id]["times"][aircraft]["kills"] = aircraft_stats["kills"]

    # Process each file
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            data = json.load(file)
        update_combined_stats(data)

    # Write the combined data to a new JSON file
    with open(output_file_path, 'w') as file:
        json.dump(combined_stats, file, indent=4)

    print(f"Combined stats written to {output_file_path}")

# Example usage
file_paths = ['data/stats/SlmodStats_server1.json','data/stats/SlmodStats_server2.json','data/stats/SlmodStats_server3.json']  # Replace with your actual file path
output_file_path = 'data/stats/combinedStatsNew.json'

combine_pilot_stats_and_output(file_paths, output_file_path)
