# src/html_generator/html_generator.py
import sqlite3, logging, os
from database.db_crud import *
from utils.stat_processing import load_combined_stats, generate_squadron_pilot_rows

def get_all_qualifications(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT qualification_id, qualification_name, qualification_description, qualification_duration FROM Qualifications")
    qualifications = cursor.fetchall()
    conn.close()
    return qualifications

def get_all_awards(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT award_id, award_name, award_description FROM Awards")
    awards = cursor.fetchall()
    conn.close()
    return awards

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
                <hr>
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

def generate_awards_qualifications_page(db_path, output_path):
    qualifications = get_all_qualifications(db_path)
    awards = get_all_awards(db_path)

    # Read the navbar HTML content
    navbar_path = 'web/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    html_content = f"""
    <html>
    <head>
        <title>Awards and Qualifications</title>
        <link rel="stylesheet" type="text/css" href="styles.css">
    </head>
    <body>
        {navbar_html}
        <div class="container">
        <h1>Awards and Qualifications</h1>
        
        <h2>Qualifications</h2>
        <table>
            <tr><th>ID</th><th>Name</th><th>Description</th><th>Duration (days)</th></tr>
    """
    for qid, qname, qdesc, qduration in qualifications:
        html_content += f"<tr><td>{qid}</td><td>{qname}</td><td>{qdesc}</td><td>{qduration//86400}</td></tr>"

    html_content += '''
        </table>
        
        <h2>Awards</h2>
        <table>
            <tr><th>ID</th><th>Name</th><th>Description</th><th>Ribbon</th></tr>
    '''
    for aid, aname, adesc in awards:
        ribbon_path = f"img/ribbons/{aname}.png"
        ribbon_img = f"<img src='{ribbon_path}' style='height:20px;'>" if os.path.exists('web/' + ribbon_path) else "No ribbon"
        html_content += f"<tr><td>{aid}</td><td>{aname}</td><td>{adesc}</td><td>{ribbon_img}</td></tr>"

    html_content += '''
        </table>
        </div>
    </body>
    </html>
    '''

    with open(output_path, "w") as file:
        file.write(html_content)

def generate_mayfly_html(db_path, output_path):
    assigned_aircraft, unassigned_aircraft = fetch_aircraft_by_squadron(db_path)

    with open(output_path, 'w') as file:
        file.write('<html><head><title>Mayfly Aircraft Listing</title></head><body>')
        file.write('<h1>Mayfly Aircraft Listing</h1>')

        # Process and write tables for assigned aircraft
        squadrons = {}
        for aircraft_id, aircraft_type, squadron_id in assigned_aircraft:
            squadrons.setdefault(squadron_id, []).append((aircraft_id, aircraft_type))
        for squadron_id, aircraft in squadrons.items():
            file.write(f'<h2>Squadron {squadron_id}</h2>')
            file.write('<table border="1"><tr><th>Aircraft ID</th><th>Type</th></tr>')
            for aircraft_id, aircraft_type in aircraft:
                file.write(f'<tr><td>{aircraft_id}</td><td>{aircraft_type}</td></tr>')
            file.write('</table>')

        # Process and write table for unassigned aircraft (Depth Maintenance)
        if unassigned_aircraft:
            file.write('<h2>Depth Maintenance</h2>')
            file.write('<table border="1"><tr><th>Aircraft ID</th><th>Type</th></tr>')
            for aircraft_id, aircraft_type in unassigned_aircraft:
                file.write(f'<tr><td>{aircraft_id}</td><td>{aircraft_type}</td></tr>')
            file.write('</table>')

        file.write('</body></html>')
