import json
from pathlib import Path
import shutil
import subprocess
from typing import Optional
import sqlite3
import csv
import deepl
import genanki
import random
import os
import openai
from constants import my_model, german, italian, auth_key

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



translator = deepl.Translator(auth_key) ## TODO: I'm pretty sure this should go in main, but not sure.

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

    for result in results:
       # print(result)
        translation = translator.translate_text(result[0], target_lang="EN-US").text

        modified_row = result[:1] + (translation,) + result[1:]
        modified_rows.append(modified_row)
        if print_results:
            print(modified_row)

    return(modified_rows)

#fetch_and_translate(title="Momo", start_date="2023-11-14T15:30", end_date="2023-11-15", ownpath="../KoboReader.sqlite", print_results=False)


def print_first_rows(author=None, title=None, start_date=None, end_date=None, ownpath=None, translate=False):
    if translate:
        results = fetch_and_translate(author, title, start_date, end_date, ownpath)
        print('Text', 'Translation', 'Annotation', 'DateCreated', 'Author', 'BookTitle')
    else:
        results = fetch_annotations(author, title, start_date, end_date, ownpath)
        print('Text', 'Annotation', 'DateCreated', 'Author', 'BookTitle')

    # Print the first few rows, adjusting as necessary for your use case.
    for row in results[:5]:
        print(row)

def save_to_csv(author=None, title=None, start_date=None, end_date=None, ownpath = None, translate = False, file_name='annotations.csv'):
    with open(file_name, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if translate == True:
            results = fetch_and_translate(author, title, start_date, end_date, ownpath)
            writer.writerow(['Text', 'Translation', 'Annotation', 'DateCreated', 'Author', 'BookTitle'])
        else:
            results = fetch_annotations(author, title, start_date, end_date, ownpath)
            writer.writerow(['Text', 'Annotation', 'DateCreated', 'Author', 'BookTitle'])
        print(results[:5])
        writer.writerows(results)

# Example usage:
#save_to_csv(title="Momo", start_date="2023-11-11", end_date="2023-11-15", translate=False, file_name="ende_annotations2.csv")
#save_to_csv(title="Momo", start_date="2023-11-11", end_date="2023-11-15", translate=True, file_name="ende_annotations2.csv")


## now, once I have a text to speech thing (and put the file name in the csv), I can already start using it in Anki. But it would be cool to have it
## create actual anki decks.



def create_deck(deck_name):
    # Generate a random number for the deck ID within a large range
    random_deck_id = random.randint(int(1e9), int(1e10))

    # Create a new genanki Deck with the random deck ID and the specified name
    my_deck = genanki.Deck(random_deck_id, deck_name)

    return my_deck


def make_note(lang, eng, audio):    ## would need to be part of a larger function where lang, eng, and audio parameters are created
  return genanki.Note(
    model=my_model,
    fields=[lang, eng, audio]
  )


openai_key = "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"
openai.api_key = openai_key
client = openai.OpenAI(api_key=openai.api_key)

def text_to_speech(text, output_file):
    """
    Convert text to speech using a specified voice and save to an output file.

    :param text: The text to be spoken.
    :param output_file: The file path to save the audio output.
    """
    try:
        # Constructing the command to use macOS's say command
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",  # other voices: 'echo', 'fable', 'onyx', 'nova', 'shimmer'
            input=text
        )

        # Executing the command
        response.stream_to_file(output_file)
        print(f"Audio saved to {output_file}")
    except Exception as e:
        print(f"Error translating '{text}': {e}")
        return ""




def make_anki_cards(deck_name, media_list, author=None, title=None, start_date=None, end_date=None, ownpath=None):
    modified_rows = fetch_and_translate(author, title, start_date, end_date, ownpath)
    for row in modified_rows:
        lang = row[0]
        eng = row[1]
        file_name = f'{lang.replace(" ", "_")[:10]}.mp3'
        formatted_file_name =f'[sound:{file_name}]'
        media_list.append(file_name)


        text_to_speech(lang, file_name)

        note = make_note(lang, eng, formatted_file_name)
        deck_name.add_note(note)


def fetch_books_and_authors(ownpath=None):
    # Connect to the SQLite database
    if ownpath is None:
        conn = sqlite3.connect(get_kobo_mountpoint() / '.kobo' / 'KoboReader.sqlite')
    else:
        conn = sqlite3.connect(ownpath)
    cursor = conn.cursor()

    # Define the SQL query to fetch unique books and their authors
    query = """
    SELECT DISTINCT
        ChapterContent.BookTitle AS Book,
        AuthorContent.Attribution AS Author
    FROM 
        Content AS ChapterContent
    LEFT JOIN 
        Content AS AuthorContent ON ChapterContent.BookID = AuthorContent.ContentID AND AuthorContent.ContentType = 6
    WHERE
        ChapterContent.ContentType = 899
    ORDER BY 
        AuthorContent.Attribution ASC
    """

    # Execute the query
    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    for result in results:
        print(f"Author:{result[1]}| Book:{result[0]}")

fetch_books_and_authors()


