import sqlite3
import logging

# Configure logging
log_filename = f"data/logs/database.log"
logging.basicConfig(filename=log_filename, level=logging.DEBUG, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Database path
db_path = 'data/db/mayfly.db'  # Update with the actual path

# SQL commands to create the tables
create_tables_commands = [
    '''CREATE TABLE IF NOT EXISTS Qualifications (
        qualification_id INTEGER PRIMARY KEY,
        qualification_name TEXT NOT NULL,
        qualification_description TEXT,
        qualification_duration INTEGER
    );''',
    '''CREATE TABLE IF NOT EXISTS Awards (
        award_id INTEGER PRIMARY KEY,
        award_name TEXT NOT NULL,
        award_description TEXT
    );''',
    '''CREATE TABLE IF NOT EXISTS Pilots (
        pilot_id TEXT PRIMARY KEY,
        pilot_name TEXT NOT NULL,
        pilot_service TEXT CHECK(pilot_service IN ('RN', 'Army', 'RAF')),
        pilot_rank TEXT NOT NULL
    );''',
    '''CREATE TABLE IF NOT EXISTS Former_Pilots (
        pilot_id TEXT PRIMARY KEY,
        pilot_name TEXT NOT NULL,
        pilot_service TEXT CHECK(pilot_service IN ('RN', 'Army', 'RAF')),
        pilot_rank TEXT NOT NULL,
        removal_date TEXT
    );''',
    '''CREATE TABLE IF NOT EXISTS Squadrons (
        squadron_id TEXT PRIMARY KEY,
        squadron_motto TEXT,
        squadron_service TEXT CHECK(squadron_service IN ('RN', 'Army', 'RAF')),
        squadron_commission_date TEXT NOT NULL,
        squadron_commanding_officer TEXT,
        squadron_aircraft_type TEXT,
        squadron_pseudo_type TEXT
    );''',
    '''CREATE TABLE IF NOT EXISTS Aircraft (
        aircraft_id TEXT PRIMARY KEY,
        aircraft_type TEXT NOT NULL,
        aircraft_pseudo TEXT,
        aircraft_state TEXT CHECK(aircraft_state IN ('S', 'US')),
        aircraft_etbol INTEGER,
        aircraft_remarks TEXT
    );''',
    '''CREATE TABLE IF NOT EXISTS Flight_Plans (
        id INTEGER PRIMARY KEY,
        aircraft_type TEXT,
        aircraft_callsign TEXT,
        flight_rules TEXT,
        type_of_flight TEXT,
        departure_aerodrome TEXT,
        departure_time TEXT,
        route TEXT,
        destination_aerodrome TEXT,
        total_estimated_elapsed_time TEXT,
        alternate_aerodrome TEXT,
        fuel_on_board TEXT,
        other_information TEXT
    );''',
    '''CREATE TABLE IF NOT EXISTS Squadron_Aircraft (
        squadron_id TEXT,
        aircraft_id TEXT,
        FOREIGN KEY (squadron_id) REFERENCES Squadrons (squadron_id),
        FOREIGN KEY (aircraft_id) REFERENCES Aircraft (aircraft_id),
        PRIMARY KEY (aircraft_id, squadron_id)
    );''',
    '''CREATE TABLE IF NOT EXISTS Squadron_Pilots (
        squadron_id TEXT,
        pilot_id TEXT,
        FOREIGN KEY (squadron_id) REFERENCES Squadrons (squadron_id),
        FOREIGN KEY (pilot_id) REFERENCES Pilots (pilot_id),
        PRIMARY KEY (pilot_id, squadron_id)
    );''',
    '''CREATE TABLE IF NOT EXISTS Pilot_Qualifications (
        pilot_id TEXT,
        qualification_id INTEGER,
        FOREIGN KEY (pilot_id) REFERENCES Pilots (pilot_id),
        FOREIGN KEY (qualification_id) REFERENCES Qualifications (qualification_id),
        PRIMARY KEY (pilot_id, qualification_id)
    );''',
    '''CREATE TABLE IF NOT EXISTS Pilot_Awards (
        pilot_id TEXT,
        award_id INTEGER,
        FOREIGN KEY (pilot_id) REFERENCES Pilots (pilot_id),
        FOREIGN KEY (award_id) REFERENCES Awards (award_id),
        PRIMARY KEY (pilot_id, award_id)
    );'''
]

# Connect to the SQLite database
conn = sqlite3.connect(db_path)

# Create the tables
with conn:
    for command in create_tables_commands:
        conn.execute(command)

# Close the connection
conn.close()

logging.info("Database and tables created successfully.")
