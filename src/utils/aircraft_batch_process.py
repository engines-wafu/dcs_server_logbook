import sqlite3
import pandas as pd

def normalize_aircraft_type(model):
    # Mapping of variant names to standard names
    variants = {
        'BAe Sea Harrier FRS1': 'Harrier',
        'BAe Sea Harrier F/A2': 'Harrier',
        'HS Harrier T4A': 'Harrier',
        'Westland Apache AH1': 'Apache',
        'BAe Hawk T2': 'Hawk',
        'McDD Phantom FGR2': 'Phantom',
        'Panavia Tornado GR1': 'Tornado',
        'Panavia Tornado GR4': 'Tornado',
        'Eurofighter Typhoon FGR4': 'Typhoon'
    }
    return variants.get(model, model)  # Return the standard name, or the original if not found

def read_csv(file_path):
    df = pd.read_csv(file_path)
    df.columns = ['aircraft_id', 'aircraft_model', 'mandatory']
    df['aircraft_model'] = df['aircraft_model'].apply(normalize_aircraft_type)
    return df

def select_aircraft(df):
    aircraft_mapping = {
        'Harrier': {'type': 'AV8BNA', 'pseudo': 'Harrier GR9'},
        'Hawk': {'type': 'T-45', 'pseudo': 'Hawk T2'},
        'Apache': {'type': 'AH-64', 'pseudo': 'Apache AH1'},
        'Phantom': {'type': 'F-14', 'pseudo': 'Phantom F4'},
        'Tornado': {'type': 'F-15', 'pseudo': 'Tornado GR4'},
        'Typhoon': {'type': 'F-16', 'pseudo': 'Tornado FGR1'},
    }

    mandatory_aircraft = df[df['mandatory'] == 'x']
    selected_aircraft = pd.DataFrame()

    for model, mapping in aircraft_mapping.items():
        model_aircraft = df[df['aircraft_model'] == model]
        mandatory_of_model = mandatory_aircraft[mandatory_aircraft['aircraft_model'] == model]
        non_mandatory_of_model = model_aircraft[model_aircraft['mandatory'] != 'x']
        remaining_selection = max(0, 18 - len(mandatory_of_model))
        random_selection = pd.DataFrame()

        if remaining_selection > 0 and len(non_mandatory_of_model) > 0:
            random_selection = non_mandatory_of_model.sample(n=remaining_selection)

        combined_selection = pd.concat([mandatory_of_model, random_selection])
        combined_selection['aircraft_type'] = mapping['type']
        combined_selection['aircraft_pseudo'] = mapping['pseudo']
        selected_aircraft = pd.concat([selected_aircraft, combined_selection])

    selected_aircraft['aircraft_state'] = 'S'
    selected_aircraft['aircraft_etbol'] = None
    selected_aircraft['aircraft_remarks'] = None

    return selected_aircraft

def insert_into_database(df, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for _, row in df.iterrows():
        cursor.execute(
            """
            INSERT INTO Aircraft (aircraft_id, aircraft_type, aircraft_pseudo, aircraft_state, aircraft_etbol, aircraft_remarks)
            VALUES (?, ?, ?, ?, ?, ?);
            """, 
            (row['aircraft_id'], row['aircraft_type'], row['aircraft_pseudo'], row['aircraft_state'], row['aircraft_etbol'], row['aircraft_remarks'])
        )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    csv_file_path = 'data/base/tail_numbers.csv'
    database_path = 'data/db/mayfly.db'

    df = read_csv(csv_file_path)
    selected_aircraft = select_aircraft(df)
    insert_into_database(selected_aircraft, database_path)
