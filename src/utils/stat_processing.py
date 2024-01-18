import os, json, sqlite3, logging
import datetime
from utils.time_management import seconds_to_hours, days_from_epoch
from database.db_crud import get_pilot_full_name

# Get the absolute path of the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Log file path
log_filename = os.path.join(project_root, "data/logs/mayfly.log")

# Ensure the log directory exists
os.makedirs(os.path.dirname(log_filename), exist_ok=True)

# Configure a separate logger for your bot
logger = logging.getLogger('stats_processor')
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler(filename=log_filename)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

def load_combined_stats(json_file_path):
    with open(json_file_path, 'r') as file:
        return json.load(file)

def ribbon_image_exists(award_name):
    image_path = f"web/img/ribbons/{award_name}.png"
    return os.path.exists(image_path)

def format_epoch_to_date(epoch_time):
    if epoch_time:
        return datetime.datetime.fromtimestamp(epoch_time).strftime('%d %b %y')
    return 'N/A'

def get_pilot_details(db_path, pilot_id, combined_stats):
    # Fetch basic pilot details
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT pilot_service, pilot_rank FROM Pilots WHERE pilot_id = ?", (pilot_id,))
    result = cursor.fetchone()
    conn.close()

    if not result:
        return None

    pilot_service, pilot_rank = result

    # Initialize total hours
    total_hours = 0

    # Get the pilot's stats
    pilot_stats = combined_stats.get(pilot_id, {})
    times = pilot_stats.get('times', {})

    try:
        if isinstance(times, dict):
            # Calculate total hours from a dictionary
            for aircraft_stats in times.values():
                if isinstance(aircraft_stats, dict):
                    total_hours += seconds_to_hours(aircraft_stats.get('total', 0))
                    logger.info(f"Seconds: {aircraft_stats.get('total')}, total: {total_hours}")
                # Skip if aircraft_stats is an empty list or any other type

    except Exception as e:
        logger.error(f"Error processing 'times' data for pilot_id {pilot_id}: {e}")
        total_hours = 0

    total_hours = round(total_hours,1)
    last_join = pilot_stats.get('lastJoin', 0)
    last_join_date = datetime.datetime.fromtimestamp(last_join).strftime('%Y-%m-%d') if last_join else "Unknown"

    return {
        'service': pilot_service,
        'rank': pilot_rank,
        'total_hours': total_hours,
        'last_join': last_join_date
    }

def get_pilot_awards_with_details(db_path, pilot_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.award_id, a.award_name, a.award_description, pa.date_issued
        FROM Awards a
        INNER JOIN Pilot_Awards pa ON a.award_id = pa.award_id
        WHERE pa.pilot_id = ?""", (pilot_id,))
    awards = [(award_id, award_name, award_description, format_epoch_to_date(date_issued), ribbon_image_exists(award_name)) for award_id, award_name, award_description, date_issued in cursor.fetchall()]
    conn.close()
    return awards

def get_pilot_qualifications_with_details(db_path, pilot_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT q.qualification_id, q.qualification_name, q.qualification_description, pq.date_issued, pq.date_expires
        FROM Qualifications q
        INNER JOIN Pilot_Qualifications pq ON q.qualification_id = pq.qualification_id
        WHERE pq.pilot_id = ?""", (pilot_id,))
    qualifications = [(qualification_id, qualification_name, qualification_description, format_epoch_to_date(date_issued), format_epoch_to_date(date_expires)) for qualification_id, qualification_name, qualification_description, date_issued, date_expires in cursor.fetchall()]
    conn.close()
    return qualifications

def generate_squadron_pilot_rows(DB_PATH, squadron_id, squadron_aircraft_type, combined_stats):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT pilot_id FROM Squadron_Pilots WHERE squadron_id = ?", (squadron_id,))
    pilot_ids = cursor.fetchall()

    pilot_hours = []
    for (pilot_id,) in pilot_ids:
        pilot_stats = combined_stats.get(pilot_id, {})

        # Check if 'times' is a dictionary and calculate total_hours
        times_data = pilot_stats.get('times', {})
        if isinstance(times_data, dict):
            total_hours = sum(seconds_to_hours(aircraft_stats.get('total', 0))
                              for aircraft_type, aircraft_stats in times_data.items()
                              if isinstance(aircraft_stats, dict))
            logger.info(f"{pilot_id} total hours: {total_hours}")
        else:
            total_hours = 0
        pilot_hours.append((pilot_id, total_hours))

    pilot_hours.sort(key=lambda x: x[1], reverse=True)

    rows_html = ""
    for pilot_id, total_hours in pilot_hours:
        pilot_name = get_pilot_full_name(DB_PATH, pilot_id)
        if not pilot_name:
            continue

        pilot_stats = combined_stats.get(pilot_id, {})
        times_data = pilot_stats.get('times', {})

        if isinstance(times_data, dict):
            type_hours = sum(seconds_to_hours(aircraft_stats.get('total', 0))
                             for aircraft_type, aircraft_stats in times_data.items()
                             if isinstance(aircraft_stats, dict) and aircraft_type.startswith(squadron_aircraft_type))

            total_kills = sum(
                sum(category.get('total', 0) for category in aircraft_stats.get('kills', {}).values())
                for aircraft_type, aircraft_stats in times_data.items()
                if isinstance(aircraft_stats, dict)
            )
        else:
            type_hours = 0
            total_kills = 0

        currency = days_from_epoch(pilot_stats.get('lastJoin', 0))
        bg_color = 'grey' if currency > 120 else 'red' if currency > 30 else 'orange' if currency > 15 else ''

        rows_html += f"""
            <tr>
                <td><a href='pilot/{pilot_id[:6]}.html'>{pilot_name}</a></td>
                <td>{type_hours:.1f}</td>
                <td>{total_hours:.1f}</td>
                <td>{total_kills}</td>
                <td style='background-color:{bg_color}'>{currency} days</td>
            </tr>
        """

    conn.close()
    return rows_html

def generate_pilot_info_page(DB_PATH, pilot_id, pilot_specific_stats, output_dir):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Fetch details for the specific pilot
    cursor.execute("SELECT pilot_id, pilot_name, pilot_service, pilot_rank FROM Pilots WHERE pilot_id = ?", (pilot_id,))
    pilot = cursor.fetchone()
    if not pilot:
        # print(f"No data found for pilot ID {pilot_id}")
        return
    pilot_id, pilot_name, pilot_service, pilot_rank = pilot

    awards = get_pilot_awards_with_details(DB_PATH, pilot_id)
    qualifications = get_pilot_qualifications_with_details(DB_PATH, pilot_id)

    # Process awards
    awards_html = "<table style='border:1'><tr><th style='width:10%'>ID</th><th style='width:50%'>Name</th><th style='width:20%'>Issued</th><th style='width:20%'>Ribbon</th></tr>"
    for award_id, award_name, award_description, date_issued, ribbon_exists in awards:
        ribbon_html = f"<img src='../img/ribbons/{award_name}.png' alt='{award_name}' style='width:50%; height:auto;'>" if ribbon_exists else "No ribbon"
        awards_html += f"<tr title='{award_description}'><td>{award_id}</td><td>{award_name}</td><td>{date_issued}</td><td style='text-align:left;'>{ribbon_html}</td></tr>"
    awards_html += "</table>"

    # Process qualifications
    today = datetime.datetime.now().date()
    qualifications_html = "<table style='border:1'><tr><th>ID</th><th>Name</th><th>Issued</th><th>Expires</th></tr>"
    for qualification_id, qualification_name, qualification_description, date_issued, date_expires in qualifications:
        date_expires_obj = datetime.datetime.strptime(date_expires, "%d %b %y").date()
        color = "red" if date_expires_obj < today else "orange" if (date_expires_obj - today).days <= 7 else ""
        qualifications_html += f"<tr title='{qualification_description}'><td>{qualification_id}</td><td>{qualification_name}</td><td>{date_issued}</td><td style='background-color:{color}'>{date_expires}</td></tr>"
    qualifications_html += "</table>"

    # Process pilot stats
    pilot_stats = pilot_specific_stats
    if not isinstance(pilot_stats.get('times'), dict):
        return  # Skip if no 'times' data

    total_hours = sum(seconds_to_hours(aircraft_stats.get('total', 0)) for aircraft_type, aircraft_stats in pilot_stats.get('times', {}).items() if isinstance(aircraft_stats, dict))

    type_hours_list = [(aircraft_type, seconds_to_hours(aircraft_stats.get('total', 0))) for aircraft_type, aircraft_stats in pilot_stats.get('times', {}).items() if isinstance(aircraft_stats, dict) and seconds_to_hours(aircraft_stats.get('total', 0)) >= 0.1]
    type_hours_list.sort(key=lambda x: x[1], reverse=True)

    type_totals_html = "<table style='border:1'><tr><th>Type</th><th>Hours</th></tr>"
    for aircraft_type, hours in type_hours_list:
        type_totals_html += f"<tr><td>{aircraft_type}</td><td>{hours:.1f}</td></tr>"
    type_totals_html += "</table>"

    aggregated_kills = {}
    for aircraft_type, aircraft_stats in pilot_stats.get('times', {}).items():
        if isinstance(aircraft_stats, dict):
            for category, kills in aircraft_stats.get('kills', {}).items():
                if isinstance(kills, dict):
                    total_kills = kills.get('total', 0)
                    aggregated_kills[category] = aggregated_kills.get(category, 0) + total_kills

    kills_html = "<table style='border:1'><tr><th>Category</th><th>Kills</th></tr>"
    for category, kills in aggregated_kills.items():
        kills_html += f"<tr><td>{category}</td><td>{kills}</td></tr>"
    kills_html += "</table>"

    last_join = pilot_stats.get('lastJoin', 0)
    last_join_date = datetime.datetime.fromtimestamp(last_join).strftime('%Y-%m-%d')

    # Construct HTML content
    pilot_html = f"""
        <html>
        <head>
            <title>Pilot Information: {pilot_name}</title>
            <meta name='viewport' content='width=device-width, initial-scale=1'>
            <link rel='stylesheet' type='text/css' href='../styles.css'>
        </head>
        <body>
            <div class='container'>
                <h1>Pilot Information File: {pilot_name}</h1>
                <h2>Basic Information</h2>
                <p>Pilot ID: {pilot_id[:6]}</p>
                <p>Pilot Service: {pilot_service}</p>
                <p>Pilot Rank: {pilot_rank}</p>
                <h2>Awards</h2>
                {awards_html if awards else '<p>No awards.</p>'}
                <h2>Qualifications</h2>
                {qualifications_html if qualifications else '<p>No qualifications.</p>'}
                <h2>Logbook</h2>
                <h3>Totals</h3>
                <p>Last Joined: {last_join_date}</p>
                <p>Total hours: {total_hours:.1f}</p>
                <h3>Type Totals</h3>
                {type_totals_html}
                <h3>Kills</h3>
                {kills_html}
            </div>
        </body>
        </html>
    """

    output_file_path = os.path.normpath(os.path.join(output_dir, f"{pilot_id[:6]}.html"))
    with open(output_file_path, "w") as file:
        file.write(pilot_html)

    conn.close()
