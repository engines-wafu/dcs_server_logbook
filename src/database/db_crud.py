import sqlite3
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
    qualification_duration_seconds = qualification_duration_days * 86400 if qualification_duration_days is not None else None

    try:
        cursor.execute("INSERT INTO Qualifications (qualification_name, qualification_description, qualification_duration) VALUES (?, ?, ?)", 
                       (qualification_name, qualification_description, qualification_duration_seconds))
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise Exception(f"Qualification already exists: {e}")
    except Exception as e:
        raise Exception(f"An error occurred: {e}")
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