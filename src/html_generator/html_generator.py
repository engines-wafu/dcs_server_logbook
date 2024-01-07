# src/html_generator/html_generator.py
import sqlite3
import logging
from database.db_crud import get_pilot_full_name
from utils.stat_processing import load_combined_stats, generate_squadron_pilot_rows

def fetch_squadron_pilots(db_path):
    """
    Fetches squadrons and their pilots from the database.
    
    :param db_path: Path to the SQLite database file.
    :return: A dictionary where keys are squadron names and values are lists of pilot names.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # SQL query to fetch squadrons and their pilots
    cursor.execute("""
        SELECT Squadrons.squadron_id, Pilots.pilot_name
        FROM Squadron_Pilots
        JOIN Squadrons ON Squadron_Pilots.squadron_id = Squadrons.squadron_id
        JOIN Pilots ON Squadron_Pilots.pilot_id = Pilots.pilot_id
        ORDER BY Squadrons.squadron_id
    """)
    data = cursor.fetchall()
    conn.close()

    # Organize data by squadrons
    squadrons = {}
    for squadron_name, pilot_name in data:
        if squadron_name not in squadrons:
            squadrons[squadron_name] = []
        squadrons[squadron_name].append(pilot_name)

    return squadrons

def generate_index_html(db_path, output_path, json_file_path):
    """
    Generates an HTML file for the index page with details for each squadron.

    :param db_path: Path to the SQLite database file.
    :param output_path: Path where the HTML file will be saved.
    :param json_file_path: Path to the combined stats JSON file.
    """

    # Load combined stats
    combined_stats = load_combined_stats(json_file_path)

    # Read the navbar HTML content
    navbar_path = 'web/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch squadron information including aircraft type
    cursor.execute("""
        SELECT squadron_id, squadron_motto, squadron_pseudo_type, squadron_commanding_officer, squadron_aircraft_type
        FROM Squadrons""")
    squadrons = cursor.fetchall()

    if not squadrons:
        logging.error("No squadrons found in the database.")
        conn.close()
        return

    # Start building the HTML content for each squadron
    squadrons_content = ""
    for squadron_id, motto, pseudo_type, commanding_officer_id, squadron_aircraft_type in squadrons:
        co_full_name = get_pilot_full_name(db_path, commanding_officer_id)
        pilot_rows_html = generate_squadron_pilot_rows(db_path, squadron_id, squadron_aircraft_type, combined_stats)

        squadrons_content += f"""
            <section>
                <h2>{squadron_id}</h2>
                <p>Motto: {motto}</p>
                <p>Type: {pseudo_type}</p>
                <h3>Commanding Officer</h3>
                <p>{co_full_name if co_full_name else 'Not available'}</p>
                <h3>Pilots</h3>
                <table style='border:1'>
                    <tr><th style='width:30%'>Name</th><th style='width:10%'>Type hours</th><th style='width:10%'>Total hours</th><th style='width:10%'>Kills</th><th style='width:10%'>Currency</th></tr>
                    {pilot_rows_html}
                </table>
            </section>
        """

    # Final HTML assembly
    final_html = f"""
    <html>
    <head>
        <title>Project Mayfly - JSW Dashboard</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <link rel='stylesheet' type='text/css' href='styles.css'>
    </head>
    <body>
        {navbar_html}
        <div class='container'>
            <h1>Joint Strike Wing Squadron Dashboard</h1>
            {squadrons_content}
        </div>
    </body>
    </html>
    """

    # Close the database connection
    conn.close()

    # Write the HTML content to a file
    with open(output_path, "w") as file:
        file.write(final_html)
