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
    Generates an HTML file for the index page with details for each squadron, including the ability to sort table columns by clicking on them.

    :param db_path: Path to the SQLite database file.
    :param output_path: Path where the HTML file will be saved.
    :param json_file_path: Path to the combined stats JSON file.
    """

    # Placeholder for auxiliary functions like load_combined_stats, get_pilot_full_name, and generate_squadron_pilot_rows
    # Ensure these functions are defined or imported in your script

    # Fetch the current date
    current_date = datetime.datetime.now().strftime("%d %B %Y")

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
                <table id="squadron{squadron_id}Table" style="border:1; cursor: pointer;">
                    <thead>
                        <tr>
                            <th style='width:30%;'>Name</th>
                            <th style='width:10%;' onclick="sortTable('squadron{squadron_id}Table', 1, true)">Type hours</th>
                            <th style='width:10%;' onclick="sortTable('squadron{squadron_id}Table', 2, true)">Total hours</th>
                            <th style='width:10%;' onclick="sortTable('squadron{squadron_id}Table', 3, true)">Kills</th>
                            <th style='width:10%;' onclick="sortTable('squadron{squadron_id}Table', 4, true)">Currency</th>
                        </tr>
                    </thead>
                    <tbody>
                        {pilot_rows_html}
                    </tbody>
                </table>
                <hr>
            </section>
        """

    # JavaScript for sorting tables
    sort_function_script = """
    <script>
    var lastSortedCol = -1;
    var sortAscending = false; // Start with descending sort by default
    
    function sortTable(tableId, col, isNumeric) {
        var table, rows, switching, i, x, y, shouldSwitch, xVal, yVal;
        table = document.getElementById(tableId);
        switching = true;
    
        // If the clicked column is different from the last, start with descending sort
        if (col != lastSortedCol) {
            sortAscending = false; // Start descending for a new column
        } else {
            // If the same column is clicked again, toggle the sorting direction
            sortAscending = !sortAscending;
        }
        lastSortedCol = col; // Update the last sorted column
    
        while (switching) {
            switching = false;
            rows = table.rows;
            for (i = 1; i < (rows.length - 1); i++) {
                shouldSwitch = false;
                x = rows[i].getElementsByTagName("TD")[col];
                y = rows[i + 1].getElementsByTagName("TD")[col];
                xVal = isNumeric ? parseFloat(x.innerHTML) || 0 : x.innerHTML.toLowerCase();
                yVal = isNumeric ? parseFloat(y.innerHTML) || 0 : y.innerHTML.toLowerCase();
    
                // Determine if rows should switch place based on the sort direction
                if (sortAscending) {
                    if (xVal > yVal) {
                        shouldSwitch = true;
                        break;
                    }
                } else {
                    if (xVal < yVal) {
                        shouldSwitch = true;
                        break;
                    }
                }
            }
            if (shouldSwitch) {
                rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                switching = true;
            }
        }
    }
    </script>
    """

    # Final HTML assembly
    final_html = f"""
    <html>
    <head>
        <title>Project Mayfly - JSW Dashboard</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <link rel='stylesheet' type='text/css' href='styles.css'>
        {sort_function_script}
    </head>
    <body>
        {navbar_html}
        <div class='container'>
            <h1>Joint Strike Wing Squadron Dashboard</h1>
            {squadrons_content}
            <p>Page generated on {current_date}</p>
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

def generate_stores_requests_page(db_path, output_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch stores request data
    cursor.execute("SELECT * FROM Stores_Request ORDER BY id DESC")
    stores_requests = cursor.fetchall()
    conn.close()

    # Read the navbar HTML content
    navbar_path = 'html/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    # HTML structure
    html_content = f"""
    <html>
    <head>
        <title>Stores Requests</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <link rel="stylesheet" type="text/css" href="styles.css">
    </head>
    <body>
        {navbar_html}
        <div class="container">
        <h1>Stores Requests</h1>
        <table>
            <tr><th>Requester</th><th>Date</th><th>Receiving Unit</th><th>Magazine Location</th><th>Need By</th><th>Stores Requested</th><th>Details</th></tr>
    """

    # Populate table rows
    for request in stores_requests:
        html_content += "<tr>" + "".join([f"<td>{item}</td>" for item in request[1:]]) + "</tr>"  # Skip the ID column

    html_content += '''
        </table>
        </div>
    </body>
    </html>
    '''

    # Write HTML content to file
    with open(output_path, 'w') as file:
        file.write(html_content)

def generate_expenditure_reports_page(db_path, output_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch expenditure report data
    cursor.execute("SELECT * FROM Expenditure_Report ORDER BY id DESC")
    expenditure_reports = cursor.fetchall()
    conn.close()

    # Read the navbar HTML content
    navbar_path = 'html/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    # HTML structure
    html_content = f"""
    <html>
    <head>
        <title>Expenditure Reports</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <link rel="stylesheet" type="text/css" href="styles.css">
    </head>
    <body>
        {navbar_html}
        <div class="container">
        <h1>Expenditure Reports</h1>
        <table>
            <tr><th>Reporter</th><th>Date</th><th>Operation</th><th>Squadron</th><th>Stores Used</th><th>BDA</th><th>AAR</th></tr>
    """

    # Populate table rows
    for report in expenditure_reports:
        html_content += "<tr>" + "".join([f"<td>{item}</td>" for item in report[1:]]) + "</tr>"  # Skip the ID column

    html_content += '''
        </table>
        </div>
    </body>
    </html>
    '''

    # Write HTML content to file
    with open(output_path, 'w') as file:
        file.write(html_content)

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

def generate_qualification_html(db_path, output_filename):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read the navbar HTML content
    navbar_path = 'html/navbar.html'
    with open(navbar_path, 'r') as file:
        navbar_html = file.read()

    # Start HTML document
    html_content = f"""
    <html>
    <head>
        <title>Pilot Qualifications</title>
        <meta name='viewport' content='width=device-width, initial-scale=1'>
        <style>
            .fixed-width-table {{
                table-layout: fixed;
                width: auto; /* Override the 100% width */
            }}
    
            .fixed-width-table th {{
                font-size: 10px;
            }}
    
            .fixed-width-table th, .fixed-width-table td {{
                width: 70px; /* Fixed width for each column */
                overflow: hidden; /* Hide text that doesn't fit */
                text-overflow: ellipsis; /* Add ellipsis to text that doesn't fit */
            }}
    
            .expired {{
                background-color: red;
                color: white; /* White text for better contrast on dark background */
            }}
    
            .warning {{
                background-color: orange;
                color: black; /* Black text for better contrast on light background */
            }}
    
            .valid {{
                background-color: green;
                color: white; /* White text for better contrast on dark background */
            }}
            
            .date-cell {{
                font-size: 8px; /* Reduced font size for dates */
            }}
        </style>
        <link rel='stylesheet' type='text/css' href='styles.css'>
    </head>
    <body>
        {navbar_html}
        <div class='container'>
        <h1>Pilot Training Records</h1>
    """

    # Fetch squadrons sorted by commission date
    cursor.execute("SELECT squadron_id FROM Squadrons ORDER BY squadron_commission_date ASC")
    squadrons = cursor.fetchall()

    for squadron in squadrons:
        # Identify applicable qualifications for the squadron
        cursor.execute("""
            SELECT DISTINCT q.qualification_id, q.qualification_name
            FROM Squadron_Qualifications sq
            JOIN Qualifications q ON sq.qualification_id = q.qualification_id
            WHERE sq.squadron_id = ?
            ORDER BY q.qualification_id ASC
        """, (squadron[0],))
        qualifications = cursor.fetchall()

        # Skip squadrons with no qualifications
        if not qualifications:
            continue

        # Squadron header
        html_content += f"<h2>{squadron[0]}</h2>"
        html_content += '<table class="fixed-width-table"><tr><th></th>' + ''.join([f"<th>{qual[1]}</th>" for qual in qualifications]) + "</tr>"

        # Fetch pilots for each squadron
        cursor.execute("""
            SELECT p.pilot_id, p.pilot_name FROM Squadron_Pilots sp
            JOIN Pilots p ON sp.pilot_id = p.pilot_id
            WHERE sp.squadron_id = ?
        """, (squadron[0],))
        pilots = cursor.fetchall()

        # Populate table rows for each pilot
        for pilot in pilots:
            html_content += f"<tr><td>{pilot[1]}</td>"
            for qual in qualifications:
                cursor.execute("""
                    SELECT pq.date_expires FROM Pilot_Qualifications pq
                    WHERE pq.pilot_id = ? AND pq.qualification_id = ?
                """, (pilot[0], qual[0]))
                expiry_epoch = cursor.fetchone()
                if expiry_epoch:
                    expiry_date = datetime.datetime.fromtimestamp(expiry_epoch[0])
                    today = datetime.datetime.now()
                    delta = expiry_date - today

                    # Determine cell color based on expiry date
                    if delta.days < 0:
                        cell_class = 'expired'
                    elif delta.days <= 14:
                        cell_class = 'warning'
                    else:
                        cell_class = 'valid'

                    expiry_date_str = expiry_date.strftime('%d %b %y')
                    html_content += f"<td class='{cell_class} date-cell'>{expiry_date_str}</td>"
                else:
                    html_content += "<td></td>"
            html_content += "</tr>"

        html_content += "</table>"

    # Close HTML document
    html_content += """
        </div>
    </body>
    </html>
    """

    # Write HTML content to file
    with open(output_filename, "w") as file:
        file.write(html_content)

    # Close database connection
    conn.close()

    return f"HTML file generated and saved as {output_filename}"