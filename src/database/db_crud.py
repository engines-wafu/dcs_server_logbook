import sqlite3
import time
import logging

# Configure logging
log_filename = f"data/logs/database.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def get_squadron_ids(db_path):
    """
    Retrieves a list of all squadron IDs from the database.

    :param db_path: Path to the SQLite database file.
    :return: A list of squadron IDs.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT squadron_id FROM Squadrons")
        squadrons = cursor.fetchall()
        # Extracting squadron_id from each tuple in the list
        return [squadron[0] for squadron in squadrons]
    except Exception as e:
        print(f"An error occurred: {e}")
        return []
    finally:
        conn.close()

def fetch_aircraft_by_squadron(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Fetch aircraft assigned to squadrons
    cursor.execute("""
        SELECT a.aircraft_id, a.aircraft_type, s.squadron_id 
        FROM Aircraft a
        LEFT JOIN Squadron_Aircraft sa ON a.aircraft_id = sa.aircraft_id
        LEFT JOIN Squadrons s ON sa.squadron_id = s.squadron_id
    """)
    assigned_aircraft = cursor.fetchall()

    # Fetch aircraft not assigned to any squadron (Depth Maintenance)
    cursor.execute("""
        SELECT aircraft_id, aircraft_type 
        FROM Aircraft 
        WHERE aircraft_id NOT IN (SELECT aircraft_id FROM Squadron_Aircraft)
    """)
    unassigned_aircraft = cursor.fetchall()

    conn.close()
    return assigned_aircraft, unassigned_aircraft

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

def get_awards(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT award_id, award_name FROM Awards")
        awards = cursor.fetchall()
    except Exception as e:
        print(f"An error occurred: {e}")
        awards = []
    finally:
        conn.close()
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

def add_squadron(db_path, squadron_id, squadron_motto, squadron_service, squadron_commission_date, squadron_commanding_officer, squadron_aircraft_type, squadron_pseudo_type):
    """
    Adds a new squadron to the database.

    :param db_path: Path to the SQLite database file.
    :param squadron_id: Unique identifier for the squadron.
    :param squadron_motto: Motto of the squadron.
    :param squadron_service: Service branch of the squadron (e.g., RN, Army, RAF).
    :param squadron_commission_date: Date of commissioning.
    :param squadron_commanding_officer: Name of the commanding officer.
    :param squadron_aircraft_type: Type of aircraft used by the squadron.
    :param squadron_pseudo_type: Pseudo type of the squadron.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Squadrons (squadron_id, squadron_motto, squadron_service, squadron_commission_date, squadron_commanding_officer, squadron_aircraft_type, squadron_pseudo_type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (squadron_id, squadron_motto, squadron_service, squadron_commission_date, squadron_commanding_officer, squadron_aircraft_type, squadron_pseudo_type))

    conn.commit()
    conn.close()

    logging.info("Squadron added: " + str(squadron_id))

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