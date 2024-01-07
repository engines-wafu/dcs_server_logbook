import os
import json
import sqlite3
import datetime
from utils.time_management import seconds_to_hours, days_from_epoch
from database.db_crud import get_pilot_full_name

def load_combined_stats(json_file_path):
    with open(json_file_path, 'r') as file:
        return json.load(file)

def generate_squadron_pilot_rows(db_path, squadron_id, squadron_aircraft_type, combined_stats):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT pilot_id FROM Squadron_Pilots WHERE squadron_id = ?", (squadron_id,))
    pilot_ids = cursor.fetchall()

    rows_html = ""
    for (pilot_id,) in pilot_ids:
        pilot_name = get_pilot_full_name(db_path, pilot_id)
        if not pilot_name:
            continue

        pilot_stats = combined_stats.get(pilot_id, {})

        times_data = pilot_stats.get('times', {})
        if not isinstance(times_data, dict):
            type_hours = 0
            total_hours = 0
            total_kills = 0
        else:
            type_hours = sum(seconds_to_hours(aircraft_stats.get('total', 0))
                             for aircraft_type, aircraft_stats in times_data.items()
                             if isinstance(aircraft_stats, dict) and aircraft_type.startswith(squadron_aircraft_type))

            total_hours = sum(seconds_to_hours(aircraft_stats.get('total', 0))
                              for aircraft_type, aircraft_stats in times_data.items()
                              if isinstance(aircraft_stats, dict))

            total_kills = sum(
                sum(category.get('total', 0) for category in aircraft_stats.get('kills', {}).values())
                for aircraft_type, aircraft_stats in times_data.items()
                if isinstance(aircraft_stats, dict)
            )

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

def generate_pilot_info_page(db_path, combined_stats, output_dir):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT pilot_id, pilot_name, pilot_service, pilot_rank FROM Pilots")
    pilots = cursor.fetchall()

    for pilot_id, pilot_name, pilot_service, pilot_rank in pilots:
        pilot_stats = combined_stats.get(pilot_id, {})

        if not isinstance(pilot_stats.get('times'), dict):
            continue

        total_hours = 0
        type_hours_list = []
        aggregated_kills = {}

        for aircraft_type, aircraft_stats in pilot_stats.get('times', {}).items():
            if not isinstance(aircraft_stats, dict):
                continue

            hours = seconds_to_hours(aircraft_stats.get('total', 0))
            if hours >= 0.1:
                total_hours += hours
                type_hours_list.append((aircraft_type, hours))

            for category, kills in aircraft_stats.get('kills', {}).items():
                if isinstance(kills, dict):
                    total_kills = kills.get('total', 0)
                    aggregated_kills[category] = aggregated_kills.get(category, 0) + total_kills

        type_hours_list.sort(key=lambda x: x[1], reverse=True)

        # Constructing HTML tables for type hours
        type_totals_html = "<table style='border:1'><tr><th style='width:20%'>Type</th><th style='width:20%'>Hours</th></tr>"
        for aircraft_type, hours in type_hours_list:
            type_totals_html += f"<tr><td>{aircraft_type}</td><td>{hours:.1f}</td></tr>"
        type_totals_html += "</table>"

        # Constructing HTML table for aggregated kills
        kills_html = "<table style='border:1'><tr><th style='width:20%'>Category</th><th style='width:20%'>Kills</th></tr>"
        for category, kills in aggregated_kills.items():
            kills_html += f"<tr><td>{category}</td><td>{kills}</td></tr>"
        kills_html += "</table>"

        last_join = pilot_stats.get('lastJoin', 0)
        last_join_date = datetime.datetime.fromtimestamp(last_join).strftime('%Y%m%d')

        pilot_html = f"""
            <html>
            <head>
                <title>Pilot Information</title>
                <meta name='viewport' content='width=device-width, initial-scale=1'>
                <link rel='stylesheet' type='text/css' href='../styles.css'>
            </head>
            <body>
                <div class='container'>
                    <h1>Pilot Information File</h1>
                    <h2>Basic Information</h2>
                    <p>Pilot ID: {pilot_id[:6]}</p>
                    <p>Pilot Service: {pilot_service}</p>
                    <p>Pilot Rank: {pilot_rank}</p>
                    <p>Pilot Name: {pilot_name}</p>
                    <h2>Qualifications</h2>
                    <ul>
                        <li>Qualification 1</li>
                        <li>Qualification 2</li>
                    </ul>
                    <h2>Awards</h2>
                    <p>No awards.</p>
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

        with open(os.path.join(output_dir, f"{pilot_id[:6]}.html"), "w") as file:
            file.write(pilot_html)

    conn.close()