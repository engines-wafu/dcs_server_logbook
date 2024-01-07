import sqlite3
import re

# Function to parse pilots.lua
def parse_pilots(file_path):
    pilots = []
    with open(file_path, 'r') as file:
        for line in file:
            match = re.match(r'\s*\{id = "(.*)", name = "(.*)", rank = "(.*)", service = "(.*)"(, awards = \{.*\})?\},', line)
            if match:
                pilots.append({
                    'id': match.group(1),
                    'name': match.group(2),
                    'rank': match.group(3),
                    'service': match.group(4)
                })
    return pilots

# Function to parse squadrons.lua (basic structure)
def parse_squadrons(file_path):
    squadrons = []
    current_squadron = None
    with open(file_path, 'r') as file:
        for line in file:
            if 'name =' in line:  # Start of a new squadron entry
                if current_squadron:
                    squadrons.append(current_squadron)  # Append the previous squadron before starting a new one
                current_squadron = {}
            if current_squadron is not None:
                if 'name =' in line:
                    current_squadron['name'] = re.search(r'name = "(.*?)"', line).group(1)
                elif 'motto =' in line:
                    current_squadron['motto'] = re.search(r'motto = "(.*?)"', line).group(1)
                elif 'type =' in line:
                    current_squadron['type'] = re.search(r'type = "(.*?)"', line).group(1)
                elif 'pseudoType =' in line:
                    current_squadron['pseudoType'] = re.search(r'pseudoType = "(.*?)"', line).group(1)

        if current_squadron:
            squadrons.append(current_squadron)  # Append the last squadron

    return squadrons

# Database path
db_path = 'data/db/mayfly.db'

# Parse the Lua files
pilots_data = parse_pilots('data/base/pilots.lua')
squadrons_data = parse_squadrons('data/base/squadrons.lua')

# Insert data into the database
conn = sqlite3.connect(db_path)
with conn:
    for pilot in pilots_data:
        sql = 'INSERT OR REPLACE INTO Pilots (pilot_id, pilot_name, pilot_rank, pilot_service) VALUES (?, ?, ?, ?)'
        conn.execute(sql, (pilot['id'], pilot['name'], pilot['rank'], pilot['service']))

    for squadron in squadrons_data:
        squadron_sql = 'INSERT OR REPLACE INTO Squadrons (squadron_id, squadron_motto, squadron_aircraft_type, squadron_pseudo_type, squadron_commission_date) VALUES (?, ?, ?, ?, ?)'
        conn.execute(squadron_sql, (squadron['name'], squadron['motto'], squadron['type'], squadron['pseudoType'], 'NONE'))

conn.close()
