import json
from pathlib import Path
import shutil
import subprocess
from typing import Optional
import sqlite3
import csv
import deepl


## function from https://github.com/karlicoss/kobuddy
def get_kobo_mountpoint(label: str='KOBOeReader') -> Optional[Path]:
    has_lsblk = shutil.which('lsblk')
    if has_lsblk:  # on Linux
        xxx = subprocess.check_output(['lsblk', '-f', '--json']).decode('utf8')
        jj = json.loads(xxx)
        devices = [d for d in jj['blockdevices'] if d.get('label', None) == label]
        kobos = []
        for d in devices:
            # older lsblk outputs single mountpoint..
            mp = d.get('mountpoint')
            if mp is not None:
                kobos.append(mp)
            mps = d.get('mountpoints')
            if mps is not None:
                assert all(p is not None for p in mps), (mps, d)
                kobos.extend(mps)
    else:
        output = subprocess.check_output(('df', '-Hl')).decode('utf8')
        output_parts = [o.split() for o in output.split('\n')]
        kobos = [o[-1] for o in output_parts if f'/Volumes/{label}' in o]

    if len(kobos) > 1:
        raise RuntimeError(f'Multiple Kobo devices detected: {kobos}')
    elif len(kobos) == 0:
        return None
    else:
        [kobo] = kobos
        return Path(kobo)


## Function to run an SQL Query filtering on below arguments (or all if arguments not specified). Prints results as tuples (I think).
def fetch_annotations(author=None, title=None, start_date=None, end_date=None, ownpath=None, print_results=False):
    # Connect to the SQLite database
    if ownpath == None:
        conn = sqlite3.connect(get_kobo_mountpoint() / '.kobo' / 'KoboReader.sqlite')
    else:
        conn = sqlite3.connect(ownpath)
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

## Example Usage:
# fetch_annotations(title="Die unendliche Geschichte") # Fetches annotations for a specific book title
# fetch_annotations(author="Mariana Mazzucato", title="Mission Economy") # Specific author and title
#fetch_annotations(start_date='2024-01', end_date='2024-02', print_results=False)

#fetch_annotations(start_date='2024-01', end_date='2024-02', print_results=True)
#fetch_annotations(start_date='2024-01', end_date='2024-02', ownpath="../KoboReader.sqlite", print_results=True)



auth_key = "39b72c5b-fd7a-4202-81e0-97503e999e6b:fx"  # Replace with your key
translator = deepl.Translator(auth_key)

def fetch_and_translate(author=None, title=None, start_date=None, end_date=None, ownpath=None, print_results=False):
    # Connect to the SQLite database
    if ownpath == None:
        conn = sqlite3.connect(get_kobo_mountpoint() / '.kobo' / 'KoboReader.sqlite')
    else:
        conn = sqlite3.connect(ownpath)
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

    modified_rows = []

    # Assuming results are in a list of tuples or similar structure
    # Adjust the printing or handling of results as needed
    if print_results:
        for result in results:
           # print(result)
            translation = translator.translate_text(result[0], target_lang="EN-US").text

            modified_row = result[:1] + (translation,) + result[1:]
            modified_rows.append(modified_row)
            print(modified_row)

    return(modified_rows)



#TODO: Change save_to_csv function to take an argument of whether it is translating or not
def save_to_csv(author=None, title=None, start_date=None, end_date=None, file_name='annotations.csv'):
    results = fetch_annotations(author, title, start_date, end_date)
    with open(file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Text', 'Annotation', 'DateCreated', 'Author', 'BookTitle'])
        print(results[:5])
        writer.writerows(results)

# Example usage:
#save_to_csv(title="Momo", file_name="ende_annotations.csv")



# Todo: add function that makes a german translation for each highlight
    # - Should probably make a csv as an intermediate step. But would be cool be able to do it all in one step. Maybe I'll try both.


# Todo: Text to speech thing
# Todo: Function that makes these translation pairs into flashcards

