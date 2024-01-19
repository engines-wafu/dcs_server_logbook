# src/html_generator/html_generator.py
import sqlite3, os, datetime
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
    navbar_path = 'html/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch squadron information including aircraft type
    cursor.execute("""
        SELECT squadron_id, squadron_motto, squadron_pseudo_type, 
               squadron_commanding_officer, squadron_aircraft_type, squadron_commission_date
        FROM Squadrons
        ORDER BY squadron_commission_date ASC""")
    squadrons = cursor.fetchall()

    if not squadrons:
        logging.error("No squadrons found in the database.")
        conn.close()
        return

    # Start building the HTML content for each squadron
    squadrons_content = ""
    for squadron_id, motto, pseudo_type, commanding_officer_id, squadron_aircraft_type, commission_date in squadrons:
        try:
            commission_epoch = int(commission_date)  # Convert string to integer
            readable_date = datetime.datetime.fromtimestamp(commission_epoch).strftime('%e %B %Y')
        except ValueError:
            readable_date = "Unknown"  # or some default value

        co_full_name = get_pilot_full_name(db_path, commanding_officer_id)
 
        pilot_rows_html = generate_squadron_pilot_rows(db_path, squadron_id, squadron_aircraft_type, combined_stats)

        squadrons_content += f"""
            <section>
                <h2>{squadron_id}</h2>
                <p>Motto: {motto}</p>
                <p>Commission Date: {readable_date}</p>
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
    navbar_path = 'html/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    html_content = f"""
    <html>
    <head>
        <title>Awards and Qualifications</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
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
        ribbon_img = f"<img src='{ribbon_path}' style='height:20px;'>" if os.path.exists('html/' + ribbon_path) else "No ribbon"
        html_content += f"<tr><td>{aid}</td><td>{aname}</td><td>{adesc}</td><td>{ribbon_img}</td></tr>"

    html_content += '''
        </table>
        </div>
    </body>
    </html>
    '''

    with open(output_path, "w") as file:
        file.write(html_content)

def generate_flight_plans_page(db_path, output_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch flight plan data
    cursor.execute("SELECT * FROM Flight_Plans ORDER BY id DESC")
    flight_plans = cursor.fetchall()
    conn.close()

    # Read the navbar HTML content
    navbar_path = 'html/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    # HTML structure
    html_content = f"""
    <html>
    <head>
        <title>Flight Plans</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <link rel="stylesheet" type="text/css" href="styles.css">
    </head>
    <body>
        {navbar_html}
        <div class="container">
        <h1>Flight Plans</h1>
        <table>
            <tr><th>Type</th><th>C/S</th><th>Flt Rules</th><th>Mission</th><th>Dep</th><th>Dep Time</th><th style='width:15%'>Rte</th><th>Dest</th><th style='width:10%'>Tot EET</th><th>Div</th><th>Fuel</th><th style='width:20%'>Rmks</th></tr>
    """

    # Populate table rows
    for plan in flight_plans:
        html_content += "<tr>" + "".join([f"<td>{item}</td>" for item in plan[1:]]) + "</tr>"  # Skip the ID column

    html_content += '''
        </table>
        </div>
    </body>
    </html>
    '''

    # Write HTML content to file
    output_file_path = output_path
    with open(output_file_path, 'w') as file:
        file.write(html_content)

    print("Flight plans page generated successfully.")

def generate_mayfly_html(db_path, output_file_path):
    # Fetch data from the database
    squadrons = get_squadron_ids(db_path)
    assigned_aircraft, unassigned_aircraft = fetch_aircraft_by_squadron(db_path)

    # Read the navbar HTML content
    navbar_path = 'html/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    # Start HTML document
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Project Mayfly - Aircraft Management</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <link rel='stylesheet' type='text/css' href='styles.css'>
    </head>
    <body>
        {navbar_html}
        <div class='container'>
    """

    # Generate squadron sections
    for squadron_id in squadrons:
        html_content += f"<div class='squadron-section'>\n<h2>{squadron_id}</h2>\n"
        squadron_pseudo_type = fetch_squadron_pseudo_type(db_path, squadron_id)
        html_content += f"<p>Aircraft type: {squadron_pseudo_type}</p>\n"
        html_content += "<h3>Aircraft</h3>\n"
        html_content += "<table>\n<tr><th>Aircraft ID</th><th>Aircraft Type</th><th>State</th><th>ETBOL</th><th>Remarks</th></tr>\n"  # Table headers

        # Generate table rows for aircraft
        for aircraft in assigned_aircraft:
            if aircraft[2] == squadron_id:  # Check if aircraft is assigned to the current squadron
                state_color = "" if aircraft[3] == 'S' else "red" if aircraft[3] == 'US' else "none"

                # Convert ETBOL from epoch to formatted date
                etbol_formatted = datetime.datetime.fromtimestamp(aircraft[4]).strftime('%d %b %y') if aircraft[4] else 'N/A'

                html_content += f"<tr><td>{aircraft[0]}</td><td>{aircraft[1]}</td><td style='background-color:{state_color};'>{aircraft[3]}</td><td>{etbol_formatted}</td><td>{aircraft[5]}</td></tr>\n"
        html_content += "</table>\n</div>\n"

    # Depth Maintenance section
    html_content += "<div class='maintenance-section'>\n<h2>Depth Maintenance</h2>\n<h3>Aircraft</h3>\n"
    html_content += "<table>\n<tr><th>Aircraft ID</th><th>Aircraft Type</th><th>State</th><th>ETBOL</th><th>Remarks</th></tr>\n"  # Table headers
    for aircraft in unassigned_aircraft:
        state_color = "" if aircraft[2] == 'S' else "red" if aircraft[2] == 'US' else "none"

        # Convert ETBOL from epoch to formatted date
        etbol_formatted = datetime.datetime.fromtimestamp(aircraft[3]).strftime('%d %b %y') if aircraft[3] else 'N/A'

        html_content += f"<tr><td>{aircraft[0]}</td><td>{aircraft[1]}</td><td style='background-color:{state_color};'>{aircraft[2]}</td><td>{etbol_formatted}</td><td>{aircraft[4]}</td></tr>\n"
    html_content += "</table>\n</div>\n"

    # Close HTML document
    html_content += "</div>\n</body>\n</html>"

    # Write to file
    with open(output_file_path, "w") as file:
        file.write(html_content)