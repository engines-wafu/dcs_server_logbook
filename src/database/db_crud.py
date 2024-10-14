import aiosqlite
import datetime
import logging
import sqlite3
import time

def create_expenditure_report_table(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create Expenditure_Report table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Expenditure_Report (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter TEXT NOT NULL,
            date TEXT NOT NULL,
            operation_name TEXT NOT NULL,
            squadron TEXT NOT NULL,
            stores_used TEXT NOT NULL,
            bda TEXT,
            aar TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def find_pilot_id_by_name(db_path, pilot_name):
    """
    Searches for a pilot in the database by name and returns their ID.

    Args:
        db_path (str): The path to the database file.
        pilot_name (str): The name of the pilot to search for.

    Returns:
        str: The ID of the pilot if found, otherwise None.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        sql_query = "SELECT pilot_id FROM Pilots WHERE pilot_name = ?"
        cursor.execute(sql_query, (pilot_name,))
        result = cursor.fetchone()

        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    finally:
        conn.close()

def get_squadron_ids(db_path):
    """
    Retrieves a list of all squadron IDs from the database, ordered by commission date.

    :param db_path: Path to the SQLite database file.
    :return: A list of squadron IDs.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Update the query to order by squadron_commission_date
        cursor.execute("SELECT squadron_id FROM Squadrons ORDER BY squadron_commission_date ASC")
        squadrons = cursor.fetchall()
        # Extracting squadron_id from each tuple in the list
        return [squadron[0] for squadron in squadrons]
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        conn.close()

def get_squadron_details(db_path, squadron_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        sql_query = "SELECT * FROM Squadrons WHERE squadron_id = ?"
        cursor.execute(sql_query, (squadron_id,))
        row = cursor.fetchone()

        if row:
            details = {
                "squadron_id": row[0],
                "squadron_motto": row[1],
                "squadron_service": row[2],
                "squadron_commission_date": row[3],
                "squadron_commanding_officer": row[4],
                "squadron_aircraft_type": row[5],
                "squadron_pseudo_type": row[6],
                "squadron_lcr_role": row[7],
                "squadron_cr_role": row[8],
                "squadron_cr_award": row[9]
            }
            return details
        else:
            return {}  # Return an empty dictionary instead of None

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return {}
    finally:
        conn.close()

def update_squadron(db_path, squadron_id, new_details):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Map from user input keys to database column names
        column_map = {
            "motto": "squadron_motto",
            "service branch": "squadron_service",
            "commission date": "squadron_commission_date",
            "commanding officer": "squadron_commanding_officer",
            "aircraft type": "squadron_aircraft_type",
            "pseudo type": "squadron_pseudo_type"
        }

        # Prepare the SQL update query
        columns = []
        values = []
        for key, value in new_details.items():
            db_column = column_map.get(key)
            if db_column:
                columns.append(f"{db_column} = ?")
                values.append(value)

        if not columns:
            print("No valid columns to update.")
            return False

        sql_update_query = f"UPDATE Squadrons SET {', '.join(columns)} WHERE squadron_id = ?"
        values.append(squadron_id)

        cursor.execute(sql_update_query, values)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def update_aircraft_state(db_path, aircraft_updates):
    """
    Updates the state, ETBOL, and remarks for one or more aircraft.

    :param db_path: Path to the database.
    :param aircraft_updates: A list of dictionaries where each dictionary contains 
                             'aircraft_id', 'aircraft_state', 'aircraft_etbol', and 'aircraft_remarks'.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for update in aircraft_updates:
        try:
            cursor.execute("""
                UPDATE Aircraft 
                SET aircraft_state = ?, aircraft_etbol = ?, aircraft_remarks = ? 
                WHERE aircraft_id = ?
            """, (update['aircraft_state'], update['aircraft_etbol'], update['aircraft_remarks'], update['aircraft_id']))
        except sqlite3.Error as e:
            print(f"Error updating aircraft {update['aircraft_id']}: {e}")

    conn.commit()
    conn.close()

def fetch_aircraft_by_squadron(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch aircraft assigned to squadrons with additional columns
    cursor.execute("""
        SELECT a.aircraft_id, a.aircraft_pseudo, s.squadron_id, a.aircraft_state, a.aircraft_etbol, a.aircraft_remarks
        FROM Aircraft a
        LEFT JOIN Squadron_Aircraft sa ON a.aircraft_id = sa.aircraft_id
        LEFT JOIN Squadrons s ON sa.squadron_id = s.squadron_id
    """)
    assigned_aircraft = cursor.fetchall()

    # Fetch aircraft not assigned to any squadron (Depth Maintenance) with additional columns
    cursor.execute("""
        SELECT aircraft_id, aircraft_pseudo, aircraft_state, aircraft_etbol, aircraft_remarks 
        FROM Aircraft 
        WHERE aircraft_id NOT IN (SELECT aircraft_id FROM Squadron_Aircraft)
    """)
    unassigned_aircraft = cursor.fetchall()

    conn.close()
    return assigned_aircraft, unassigned_aircraft

def fetch_squadron_pseudo_type(db_path, squadron_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT squadron_pseudo_type FROM Squadrons WHERE squadron_id = ?", (squadron_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Unknown"

def fetch_aircraft_types(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT aircraft_pseudo FROM Aircraft")
    types = cursor.fetchall()
    conn.close()
    
    return [t[0] for t in types]  # Returning a list of aircraft types

def fetch_aircraft_ids_by_type(db_path, aircraft_pseudo):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT aircraft_id FROM Aircraft WHERE aircraft_pseudo = ?", (aircraft_pseudo,))
    aircraft_ids = cursor.fetchall()
    conn.close()
    
    return [a[0] for a in aircraft_ids]  # Returning a list of aircraft IDs

def fetch_squadrons_for_type(db_path, aircraft_type):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT squadron_id FROM Squadrons WHERE squadron_pseudo_type = ?", (aircraft_type,))
    squadrons = cursor.fetchall()
    conn.close()
    
    return [s[0] for s in squadrons]  # Returning a list of squadron IDs

def assign_aircraft_to_squadron(db_path, squadron_id, aircraft_ids):
    """Assigns a list of aircraft to a squadron."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for aircraft_id in aircraft_ids:
        try:
            cursor.execute("INSERT INTO Squadron_Aircraft (squadron_id, aircraft_id) VALUES (?, ?)", (squadron_id, aircraft_id))
        except sqlite3.IntegrityError as e:
            print(f"Error assigning aircraft {aircraft_id} to squadron {squadron_id}: {e}")

    conn.commit()
    conn.close()

def send_aircraft_to_maintenance(db_path, aircraft_ids):
    """Removes a list of aircraft from the Squadron_Aircraft table, sending them to maintenance."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    for aircraft_id in aircraft_ids:
        cursor.execute("DELETE FROM Squadron_Aircraft WHERE aircraft_id = ?", (aircraft_id,))

    conn.commit()
    conn.close()

def add_award_to_database(db_path, award_name, award_description):
    """
    Inserts a new award into the Awards table.

    :param db_path: Path to the SQLite database file.
    :param award_name: Name of the award.
    :param award_description: Description of the award.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO Awards (award_name, award_description) VALUES (?, ?)", (award_name, award_description))
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise Exception(f"Award already exists: {e}")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")
    finally:
        conn.close()

def add_qualification_to_database(db_path, qualification_name, qualification_description, qualification_duration_days):
    """
    Inserts a new qualification into the Qualifications table.

    :param db_path: Path to the SQLite database file.
    :param qualification_name: Name of the qualification.
    :param qualification_description: Description of the qualification.
    :param qualification_duration_days: Duration of the qualification in days (optional, can be None).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Convert duration from days to seconds (1 day = 86400 seconds)
    duration_in_seconds = qualification_duration_days * 86400  # Convert days to seconds

    try:
        cursor.execute("INSERT INTO Qualifications (qualification_name, qualification_description, qualification_duration) VALUES (?, ?, ?)", 
                       (qualification_name, qualification_description, duration_in_seconds))
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise Exception(f"Qualification already exists: {e}")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")
    finally:
        conn.close()

def get_all_pilots(db_path):
    """
    Retrieves all pilots and their IDs from the database.

    :param db_path: Path to the SQLite database file.
    :return: A list of tuples, each containing a pilot's ID and name.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Assuming your table is named 'Pilots' and has columns 'pilot_id' and 'pilot_name'
        query = "SELECT pilot_id, pilot_name FROM Pilots"
        cursor.execute(query)

        # Fetch all results
        pilots = cursor.fetchall()

        return pilots

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        conn.close()

async def get_awards(db_path):
    async with aiosqlite.connect(db_path) as conn:
        async with conn.cursor() as cursor:
            try:
                await cursor.execute("SELECT award_id, award_name FROM Awards")
                awards = await cursor.fetchall()
            except Exception as e:
                print(f"An error occurred: {e}")
                awards = []
    return awards

def get_qualifications(db_path):
    """
    Retrieves all qualifications from the database.

    :param db_path: Path to the SQLite database file.
    :return: A list of tuples containing qualification details.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT qualification_id, qualification_name, qualification_duration FROM Qualifications")
        qualifications = cursor.fetchall()
    except Exception as e:
        print(f"An error occurred: {e}")
        qualifications = []
    finally:
        conn.close()

    return qualifications

def assign_award_to_pilot(db_path, pilot_id, award_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO Pilot_Awards (pilot_id, award_id, date_issued) VALUES (?, ?, ?)", 
                       (pilot_id, award_id, int(time.time())))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Award already assigned to this pilot.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def assign_qualification_to_pilot(db_path, pilot_id, qualification_id, date_issued, date_expires):
    """
    Assigns a qualification to a pilot and updates the database.

    :param db_path: Path to the SQLite database file.
    :param pilot_id: Unique identifier of the pilot.
    :param qualification_id: Unique identifier of the qualification.
    :param date_issued: The date the qualification was issued (epoch time).
    :param date_expires: The date the qualification expires (epoch time).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO Pilot_Qualifications (pilot_id, qualification_id, date_issued, date_expires) VALUES (?, ?, ?, ?)", 
                       (pilot_id, qualification_id, date_issued, date_expires))
        conn.commit()
    except sqlite3.IntegrityError as e:
        print(f"Qualification already assigned to this pilot: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def get_pilot_awards(db_path, pilot_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT a.award_id, a.award_name FROM Awards a INNER JOIN Pilot_Awards pa ON a.award_id = pa.award_id WHERE pa.pilot_id = ?", (pilot_id,))
        awards = cursor.fetchall()
    except Exception as e:
        print(f"An error occurred: {e}")
        awards = []
    finally:
        conn.close()
    return awards

def get_pilot_qualifications(db_path, pilot_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT q.qualification_id, q.qualification_name FROM Qualifications q INNER JOIN Pilot_Qualifications pq ON q.qualification_id = pq.qualification_id WHERE pq.pilot_id = ?", (pilot_id,))
        qualifications = cursor.fetchall()
    except Exception as e:
        print(f"An error occurred: {e}")
        qualifications = []
    finally:
        conn.close()
    return qualifications

def remove_award_from_pilot(db_path, pilot_id, award_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Pilot_Awards WHERE pilot_id = ? AND award_id = ?", (pilot_id, award_id))
        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def remove_qualification_from_pilot(db_path, pilot_id, qualification_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM Pilot_Qualifications WHERE pilot_id = ? AND qualification_id = ?", (pilot_id, qualification_id))
        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def add_pilot_to_db(db_path, pilot_id, pilot_name, pilot_service, pilot_rank):
    """Adds a new pilot to the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        sql_command = """
            INSERT INTO Pilots (pilot_id, pilot_name, pilot_service, pilot_rank)
            VALUES (?, ?, ?, ?)
        """
        cursor.execute(sql_command, (pilot_id, pilot_name, pilot_service, pilot_rank))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def add_squadron_to_db(db_path, squadron_id, squadron_motto, squadron_service, squadron_commission_date, squadron_commanding_officer, squadron_aircraft_type, squadron_pseudo_type):
    logging.info(f"Adding new squadron to the database: {squadron_id}")
    try:
        # Log the connection attempt
        logging.debug(f"Connecting to the database at {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Log the execution of the SQL command
        logging.debug("Preparing to execute INSERT command")
        sql_command = """
            INSERT INTO Squadrons (squadron_id, squadron_motto, squadron_service, squadron_commission_date, squadron_commanding_officer, squadron_aircraft_type, squadron_pseudo_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        logging.debug(f"SQL Command: {sql_command}")
        logging.debug(f"Values: {squadron_id}, {squadron_motto}, {squadron_service}, {squadron_commission_date}, {squadron_commanding_officer}, {squadron_aircraft_type}, {squadron_pseudo_type}")
        
        cursor.execute(sql_command, (squadron_id, squadron_motto, squadron_service, squadron_commission_date, squadron_commanding_officer, squadron_aircraft_type, squadron_pseudo_type))

        # Log the commit
        logging.debug("Committing the transaction")
        conn.commit()

        # Log the closing of the connection
        logging.debug("Closing the database connection")
        conn.close()

        logging.info("Squadron successfully added to the database.")
        return True
    except Exception as e:
        logging.exception("Exception occurred while adding squadron to the database: ", exc_info=e)
        return False

def update_pilot(db_path, pilot_id, new_details):
    """Updates a pilot's details in the database.

    Args:
        db_path (str): The path to the database file.
        pilot_id (str): The ID of the pilot to update.
        new_details (dict): A dictionary containing the pilot's updated details.
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Prepare the SQL update query
        updates = []
        values = []
        for key, value in new_details.items():
            # Map the user-friendly field names to database column names
            db_column = {
                "name": "pilot_name",
                "service": "pilot_service",
                "rank": "pilot_rank"
            }.get(key)

            if db_column:
                updates.append(f"{db_column} = ?")
                values.append(value)

        if not updates:
            print("No valid fields to update.")
            return False

        # Add the pilot_id to the values list for the WHERE clause
        values.append(pilot_id)

        # Execute the update query
        sql_update_query = f"UPDATE Pilots SET {', '.join(updates)} WHERE pilot_id = ?"
        cursor.execute(sql_update_query, values)
        conn.commit()

        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def edit_squadron(db_path, squadron_id, squadron_motto=None, squadron_service=None, squadron_commission_date=None, squadron_commanding_officer=None, squadron_aircraft_type=None, squadron_pseudo_type=None):
    """
    Edits an existing squadron in the database.

    :param db_path: Path to the SQLite database file.
    :param squadron_id: Unique identifier for the squadron.
    :param squadron_motto: Motto of the squadron.
    :param squadron_service: Service branch of the squadron.
    :param squadron_commission_date: Date of commissioning.
    :param squadron_commanding_officer: Name of the commanding officer.
    :param squadron_aircraft_type: Type of aircraft used by the squadron.
    :param squadron_pseudo_type: Pseudo type of the squadron.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Prepare the SQL query with the parameters that need to be updated
    query = "UPDATE Squadrons SET "
    params = []
    if squadron_motto is not None:
        query += "squadron_motto = ?, "
        params.append(squadron_motto)
    if squadron_service is not None:
        query += "squadron_service = ?, "
        params.append(squadron_service)
    if squadron_commission_date is not None:
        query += "squadron_commission_date = ?, "
        params.append(squadron_commission_date)
    if squadron_commanding_officer is not None:
        query += "squadron_commanding_officer = ?, "
        params.append(squadron_commanding_officer)
    if squadron_aircraft_type is not None:
        query += "squadron_aircraft_type = ?, "
        params.append(squadron_aircraft_type)
    if squadron_pseudo_type is not None:
        query += "squadron_pseudo_type = ?, "
        params.append(squadron_pseudo_type)

    query = query.strip(", ")  # Remove the trailing comma
    query += " WHERE squadron_id = ?"
    params.append(squadron_id)

    cursor.execute(query, params)
    conn.commit()
    conn.close()

    logging.info("Squadron edited: " + str(squadron_id))

def delete_squadron(db_path, squadron_id):
    """
    Deletes a squadron from the database.

    :param db_path: Path to the SQLite database file.
    :param squadron_id: The ID of the squadron to be deleted.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Delete the squadron from the Squadrons table
    cursor.execute("DELETE FROM Squadrons WHERE squadron_id = ?", (squadron_id,))

    conn.commit()
    conn.close()

    logging.info("Squadron deleted: " + str(squadron_id))

def move_pilot_to_former(db_path, pilot_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Fetch the pilot's details
        cursor.execute("SELECT * FROM Pilots WHERE pilot_id = ?", (pilot_id,))
        pilot_data = cursor.fetchone()

        if pilot_data:
            # Add removal date and insert into Former_Pilots
            removal_date = datetime.datetime.now().strftime("%Y-%m-%d")
            cursor.execute("INSERT INTO Former_Pilots VALUES (?, ?, ?, ?, ?)", 
                           (*pilot_data, removal_date))

            # Delete the pilot from Pilots
            cursor.execute("DELETE FROM Pilots WHERE pilot_id = ?", (pilot_id,))
            conn.commit()

        return True
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return False
    finally:
        conn.close()

def get_pilot_full_name(db_path, pilot_id):
    """
    Fetches the full name of a pilot based on the pilot_id.

    :param db_path: Path to the SQLite database file.
    :param pilot_id: Unique identifier of the pilot.
    :return: Concatenated string of pilot's rank, name, and service, or None if not found.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch pilot details
    cursor.execute("SELECT pilot_rank, pilot_name, pilot_service FROM Pilots WHERE pilot_id = ?", (pilot_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        # Concatenate the pilot's rank, name, and service
        pilot_rank, pilot_name, pilot_service = result
        return f"{pilot_rank} {pilot_name}"
    else:
        return None

def get_pilot_name_and_rank(db_path, pilot_id):
    # This function needs to query the database to get the pilot's name and rank
    # Placeholder implementation - replace this with actual database query
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT pilot_name, pilot_rank FROM Pilots WHERE pilot_id = ?", (pilot_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else ("Unknown", "Unknown")

def get_pilot_name(db_path, pilot_id):
    """
    Fetches the name of a pilot based on the pilot_id.

    :param db_path: Path to the SQLite database file.
    :param pilot_id: Unique identifier of the pilot.
    :return: String of pilot's name or None if not found.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch pilot details
    cursor.execute("SELECT pilot_name FROM Pilots WHERE pilot_id = ?", (pilot_id,))
    result = cursor.fetchone()

    conn.close()

    if result:
        pilot_name = result[0]  # Accessing the first element of the tuple
        return pilot_name
    else:
        return None

def assign_co_to_squadron(db_path, pilot_id, squadron_id):
    """
    Assigns a pilot to be the commanding officer of a squadron.

    :param db_path: Path to the SQLite database file.
    :param pilot_id: Unique identifier of the pilot.
    :param squadron_id: Unique identifier of the squadron.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE Squadrons SET squadron_commanding_officer = ? WHERE squadron_id = ?", (pilot_id, squadron_id))
        conn.commit()
        logging.info(f"Pilot {pilot_id} assigned as CO of Squadron {squadron_id}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

    logging.info("Pilot " + get_pilot_name(db_path, pilot_id) + " assigned to command of " + str(squadron_id))

def assign_pilot_to_squadron(db_path, pilot_id, squadron_id):
    """
    Assigns a pilot to a squadron.

    :param db_path: Path to the SQLite database file.
    :param pilot_id: Unique identifier of the pilot.
    :param squadron_id: Unique identifier of the squadron.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO Squadron_Pilots (squadron_id, pilot_id) VALUES (?, ?)", (squadron_id, pilot_id))
        conn.commit()
    except sqlite3.IntegrityError:
        print(f"Pilot {pilot_id} is already assigned to Squadron {squadron_id}.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

    logging.info("Pilot " + get_pilot_name(db_path, pilot_id) + " assigned to " + str(squadron_id))

def move_pilot_to_squadron(db_path, pilot_id, new_squadron_id):
    """
    Moves a pilot to a different squadron.

    :param db_path: Path to the SQLite database file.
    :param pilot_id: ID of the pilot.
    :param new_squadron_id: ID of the new squadron to move the pilot to.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("UPDATE Squadron_Pilots SET squadron_id = ? WHERE pilot_id = ?", (new_squadron_id, pilot_id))

    conn.commit()
    conn.close()

    logging.info("Pilot " + get_pilot_name(db_path, pilot_id) + " moved to " + str(squadron_id))

def remove_pilot_from_squadron(db_path, pilot_id):
    """
    Removes a pilot from their squadron.

    :param db_path: Path to the SQLite database file.
    :param pilot_id: ID of the pilot to remove from the squadron.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Squadron_Pilots WHERE pilot_id = ?", (pilot_id,))

    conn.commit()
    conn.close()

    logging.info("Pilot " + get_pilot_name(db_path, pilot_id) + " removed from all squadrons")

def find_pilot_id_by_name(db_path, pilot_name):
    """
    Finds a pilot's ID based on a given name, with some tolerance for case and whitespace variations.

    :param db_path: Path to the SQLite database file.
    :param pilot_name: Name of the pilot.
    :return: The pilot's ID if found, otherwise None.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Using LIKE for a case-insensitive and flexible match
    cursor.execute("SELECT pilot_id FROM Pilots WHERE pilot_name LIKE ?", (f"%{pilot_name.strip()}%",))

    result = cursor.fetchone()
    conn.close()

    return result[0] if result else None

def insert_expenditure_report(db_path, reporter, date, operation_name, squadron, stores_used, bda=None, aar=None):
    """
    Inserts a new expenditure report into the Expenditure_Report table.

    :param db_path: Path to the SQLite database file.
    :param reporter: The name of the reporter (eventually from Discord username).
    :param date: The date of the report (could be a timestamp or string).
    :param operation_name: The name of the operation or exercise.
    :param squadron: The squadron involved in the operation.
    :param stores_used: Free text listing the weapons or stores used.
    :param bda: Optional battle damage report (BDA).
    :param aar: Optional after-action report (AAR).
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Expenditure_Report (reporter, date, operation_name, squadron, stores_used, bda, aar)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (reporter, date, operation_name, squadron, stores_used, bda, aar))

        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

    return True

def insert_flight_plan(db_path, aircraft_type, aircraft_callsign, flight_rules, type_of_flight, departure_aerodrome, departure_time, route, destination_aerodrome, total_estimated_elapsed_time, alternate_aerodrome, fuel_on_board, other_information):
    """
    Inserts a new flight plan into the Flight_Plans table.

    :param db_path: Path to the SQLite database file.
    :param aircraft_type: Type of the aircraft.
    :param aircraft_callsign: Callsign of the aircraft.
    :param flight_rules: Flight rules (e.g., IFR, VFR).
    :param type_of_flight: Type of the flight (e.g., commercial, private).
    :param departure_aerodrome: Aerodrome of departure.
    :param departure_time: Estimated time of departure.
    :param route: Planned route.
    :param destination_aerodrome: Destination aerodrome.
    :param total_estimated_elapsed_time: Total estimated elapsed time for the flight.
    :param alternate_aerodrome: Alternate aerodrome in case of changes.
    :param fuel_on_board: Amount of fuel on board.
    :param other_information: Any other relevant information.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO Flight_Plans (aircraft_type, aircraft_callsign, flight_rules, type_of_flight, departure_aerodrome, departure_time, route, destination_aerodrome, total_estimated_elapsed_time, alternate_aerodrome, fuel_on_board, other_information)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (aircraft_type, aircraft_callsign, flight_rules, type_of_flight, departure_aerodrome, departure_time, route, destination_aerodrome, total_estimated_elapsed_time, alternate_aerodrome, fuel_on_board, other_information))

        conn.commit()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

    return True

def get_pilot_squadron_id(db_path, pilot_id):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = "SELECT squadron_id FROM Squadron_Pilots WHERE pilot_id = ?"
        cursor.execute(query, (pilot_id,))
        result = cursor.fetchone()

        conn.close()

        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None

# Tests for db interactions

db_path = 'data/db/mayfly.db'
pilot_id = 'ea2dca05dc204673da916448f77f00f1'
squadron_id = '801 NAS'
pilot_name = 'raz'

# edit_squadron(db_path, squadron_id, squadron_commanding_officer=pilot_id)
# add_squadron(db_path, squadron_id, squadron_motto='Do stuff', squadron_service='RN', squadron_commission_date='1000', squadron_commanding_officer=pilot_id, squadron_aircraft_type='GR9', squadron_pseudo_type='GR9')
# delete_squadron(db_path,squadron_id)
# print(get_pilot_full_name(db_path, pilot_id))
# print(get_pilot_name(db_path, pilot_id))
# assign_pilot_to_squadron(db_path, pilot_id, squadron_id)
# move_pilot_to_squadron(db_path, pilot_id, squadron_id)
# remove_pilot_from_squadron(db_path, pilot_id)
# print(find_pilot_id_by_name(db_path, pilot_name))
# add_squadron_to_db(db_path, "809 NAS", "Do zooms", "RN", 11111111, "Nil", "AV8BNA", "Harrier GR9")