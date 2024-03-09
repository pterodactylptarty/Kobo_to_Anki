import sqlite3


def print_all_annotations(db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query to select all annotations
                                                                                                                                             ""
                                                                                                                                                " # Adjust 'Annotations' if the table name is different)

    # Execute the query
    cursor.execute(query)

    # Fetch and print all records
    annotations = cursor.fetchall()
    for annotation in annotations:
        print(annotation)  # Adjust this line to format the output as you like

    # Close the database connection
    conn.close()

# Example usage
# db_path = 'path/to/your/kobo/database.db'
print_all_annotations("../KoboReader.sqlite")
