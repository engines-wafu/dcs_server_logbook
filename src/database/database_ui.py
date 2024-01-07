import tkinter as tk
import sqlite3

def query_database():
    # Connect to SQLite database
    conn = sqlite3.connect('data/db/mayfly.db')
    cursor = conn.cursor()

    # Query the database
    cursor.execute("SELECT * FROM Pilots")  # Example query
    records = cursor.fetchall()

    # Close the connection
    conn.close()
    return records

def display_records(records):
    for row in records:
        listbox.insert(tk.END, row)

app = tk.Tk()
app.title("Database Viewer")

listbox = tk.Listbox(app)
listbox.pack(fill=tk.BOTH, expand=1)

# Fetch and display records
records = query_database()
display_records(records)

app.mainloop()
