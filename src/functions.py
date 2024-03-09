import sqlite3

def fetch_annotations(author=None, title=None):
    # Base query that fetches all annotations

    # Connect to the SQLite database
    conn = sqlite3.connect('../KoboReader.sqlite')
    cursor = conn.cursor()

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
        1=1
    """

    # Initialize an empty list to hold parameters for SQL query
    params = []

    # Add conditions to the query based on user input
    if author:
        query += " AND AuthorContent.Attribution = ?"
        params.append(author)

    if title:
        query += " AND ChapterContent.BookTitle = ?"
        params.append(title)

    # Assuming db_connection is your database connection object
        # Execute the query
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()

    # Assuming results are in a list of tuples or similar structure
    # Adjust the printing or handling of results as needed
    for result in results:
        print(result)

# Example usage:
#fetch_annotations() # Fetches all annotations
#fetch_annotations(author="Michael Ende") # Fetches annotations for a specific author
#fetch_annotations(title="Die unendliche Geschichte") # Fetches annotations for a specific book title
# fetch_annotations(author="Mariana Mazzucato", title="Mission Economy") # Specific author and title
