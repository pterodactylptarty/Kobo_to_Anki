import sqlite3
import csv

## Function to run an SQL Query filtering on below arguments (or all if arguments not specified). Prints results as tuples (I think).
def fetch_annotations(author=None, title=None, start_date=None, end_date=None, print_results=False):

    # Connect to the SQLite database
    conn = sqlite3.connect('../KoboReader.sqlite')
    cursor = conn.cursor()

    query = """
    SELECT 
        Bookmark.Text,
        Bookmark.Annotation,
        Bookmark.DateCreated,
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
    # Add date range to the query

    if start_date and end_date:
        query += " AND Bookmark.DateCreated BETWEEN ? AND ?"
        params.append(start_date)
        params.append(end_date)

    query += " ORDER BY Bookmark.DateCreated ASC"

        # Execute the query
    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()


    # Assuming results are in a list of tuples or similar structure
    # Adjust the printing or handling of results as needed
    if print_results:
        for result in results:
            print(result)

    return results


def csv_test(author=None, title=None, start_date=None, end_date=None):
    print(fetch_annotations(author, title, start_date, end_date))

csv_test()
csv_test(start_date=2023, end_date=2024)
def save_to_csv(author=None, title=None, start_date=None, end_date=None, file_name='annotations.csv'):
    results = fetch_annotations(author, title, start_date, end_date)
    with open(file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Text', 'Annotation', 'DateCreated', 'Author', 'BookTitle'])
        print(results[:5])
        writer.writerows(results)
# Example usage:
#fetch_annotations() # Fetches all annotations
#fetch_annotations(author="Michael Ende") # Fetches annotations for a specific author
#fetch_annotations(title="Die unendliche Geschichte") # Fetches annotations for a specific book title
# fetch_annotations(author="Mariana Mazzucato", title="Mission Economy") # Specific author and title
#fetch_annotations(start_date='2024-01', end_date='2024-02', print_results=False)

save_to_csv(title="Momo", file_name="ende_annotations.csv")

