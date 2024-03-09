import sqlite3

def print_all_annotations_with_book_info(db_path):
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query to select specific columns from Bookmark and join with Content for book information
        query = """
SELECT 
    Bookmark.Text AS Annotation,
    AuthorContent.Attribution AS Author,
    ChapterContent.BookTitle
FROM 
    Bookmark
INNER JOIN 
    Content AS ChapterContent ON Bookmark.ContentID = ChapterContent.ContentID
LEFT JOIN 
    Content AS AuthorContent ON ChapterContent.BookID = AuthorContent.ContentID AND AuthorContent.BookID IS NULL
WHERE
    AuthorContent.Attribution = 'Franz Kafka'

        """

        # Execute the query
        cursor.execute(query)

        # Fetch and print all records
        annotations = cursor.fetchall()
        for annotation in annotations:
            print(annotation)

    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        # Close the database connection
        if conn:
            conn.close()

# Example usage
print_all_annotations_with_book_info('../KoboReader.sqlite')


