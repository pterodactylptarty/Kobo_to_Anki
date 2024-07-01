from pathlib import Path
import shutil
import subprocess
import sqlite3
import json
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import deepl
import random
import datetime
import genanki
import requests
import os
import threading
import sys
from queue import Queue, Empty
import asyncio
import logging
import aiohttp
from openai import AsyncOpenAI
from typing import Optional
from api_keys import openai_key, DeepL
from concurrent.futures import ThreadPoolExecutor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Global variable to store the asyncio loop
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
task_queue = Queue()


is_running = False

executor = ThreadPoolExecutor()



media_list = []


processed_cards = {}
current_progress = 0
current_phase = "Translation"


# Initialize API clients
async_client = AsyncOpenAI(api_key=openai_key)
translator = deepl.Translator(DeepL)

# Semaphore to limit concurrent API calls
sem = asyncio.Semaphore(2)  # Adjust this number based on API rate limits


my_css = """
.card {
font-family: arial;
font-size: 20px;
text-align: center;
color: black;
background-color: white;
}


.english-sentence {
font-size: 19px;
font-style: italic;
}

"""

my_model = genanki.Model(
  1702925615000,
  'Python Test Model',
  fields=[
    {'name': 'Language'},
    {'name': 'English'},
    {'name': 'MyMedia'}
  ],
  templates=[
    {
      'name': 'Card 1',
      'qfmt': '{{Language}}<br>{{MyMedia}}',
      'afmt': '{{FrontSide}}<hr id="answer"><div class="english-sentence">{{English}}</div>',
    },
  ],
    css=my_css

)



# Function from https://github.com/karlicoss/kobuddy
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

def fetch_books_and_authors(sort_by='Author', ownpath=None):
    # Connect to the SQLite database
    if ownpath is None:
        kobo_path = get_kobo_mountpoint()
        if kobo_path is None:
            messagebox.showerror("Error", "No Kobo device detected")
            return
        conn = sqlite3.connect(kobo_path / '.kobo' / 'KoboReader.sqlite')
    else:
        conn = sqlite3.connect(ownpath)
    cursor = conn.cursor()

    if sort_by == 'Author': sort_column = 'Content.Attribution'
    elif sort_by == 'Book': sort_column = 'Content.Title'
    elif sort_by == 'Date Added': sort_column = 'Content.___SyncTime'

    query = f"""
    SELECT DISTINCT
        Content.Title AS Book,
        Content.Attribution AS Author,
        Content.___SyncTime 
    FROM 
        Content 
    WHERE
        Content.DateLastRead IS NOT NULL AND
        Content.Title IS NOT NULL AND
        Content.Attribution IS NOT NULL
    ORDER BY 
        {sort_column} ASC
    """

    cursor.execute(query)
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    # Display results in the listbox
    listbox.delete(0, tk.END)

    # Add a header
    header = f"{'Author':<30} | {'Book':<40} | {'Date Added':<20}"
    listbox.insert(tk.END, header)
    listbox.insert(tk.END, "-" * len(header))  # Add a separator line


    for result in results:
        author = result[1][:28] + '..' if len(result[1]) > 30 else result[1]
        book = result[0][:38] + '..' if len(result[0]) > 40 else result[0]
        date_added = result[2][:19]  # Truncate to remove milliseconds if present

        formatted_line = f"{author:<30} | {book:<40} | {date_added:<20}"
        listbox.insert(tk.END, formatted_line)

    listbox.config(font=("Courier", 16))

def fetch_annotations(author=None, title=None, start_date=None, end_date=None, ownpath=None):
    if ownpath is None:
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

    params = []

    if author:
        query += " AND AuthorContent.Attribution = ?"
        params.append(author)

    if title:
        query += " AND ChapterContent.BookTitle = ?"
        params.append(title)

    if start_date and end_date:
        query += " AND Bookmark.DateCreated BETWEEN ? AND ?"
        params.append(start_date)
        params.append(end_date)

    query += " ORDER BY Bookmark.DateCreated ASC"

    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()
    conn.close()

    return results


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

    params = []

    if author:
        query += " AND AuthorContent.Attribution = ?"
        params.append(author)

    if title:
        query += " AND ChapterContent.BookTitle = ?"
        params.append(title)

    if start_date and end_date:
        query += " AND Bookmark.DateCreated BETWEEN ? AND ?"
        params.append(start_date)
        params.append(end_date)

    query += " ORDER BY Bookmark.DateCreated ASC"

    cursor.execute(query, params)
    results = cursor.fetchall()
    cursor.close()

    modified_rows = []
    for index, result in enumerate(results, 1):
        original_text = result[0]
        translation = translator.translate_text(original_text, target_lang="EN-US").text

        modified_row = result[:1] + (translation,) + result[1:]
        modified_rows.append(modified_row)

        # Yield progress
        yield index, len(results), original_text, translation

    return modified_rows


def display_annotations(annotations):
    listbox.delete(0, tk.END)  # Clear the listbox

    if not annotations:
        listbox.insert(tk.END, "No annotations found.")
        return

    # Add headers
    headers = ["Text", "Date Created"]
    listbox.insert(tk.END, f"{'Text':<80} | {'Date Created':<20}")
    listbox.insert(tk.END, "-" * 102)  # Separator line

    for annotation in annotations:
        text = annotation[0]  # First field is Text
        date_created = annotation[2]  # Third field is Date Created

        # Format the text field
        if len(text) > 77:
            formatted_text = text[:77] + "..."
        else:
            formatted_text = text.ljust(80)

        # Format the date
        formatted_date = date_created[:19]  # Assuming the date is in ISO format, this will trim any milliseconds

        formatted_line = f"{formatted_text} | {formatted_date:<20}"
        listbox.insert(tk.END, formatted_line)

    # Adjust column widths
    listbox.config(width=102)  # Total width: 80 (Text) + 2 (separator) + 20 (Date)
def fetch_and_display_annotations():
    author = author_entry.get()
    title = title_entry.get()
    start_date = start_date_picker.get_date().strftime("%Y-%m-%d") if start_date_picker.get() else None
    end_date = end_date_picker.get_date().strftime("%Y-%m-%d") if end_date_picker.get() else None

    annotations = fetch_annotations(author, title, start_date, end_date)
    display_annotations(annotations)

def fetch_books_and_authors_with_sort():
    sort_by = sort_option.get()
    fetch_books_and_authors(sort_by)

def on_listbox_select(event):
    selection = listbox.curselection()
    if selection:
        index = selection[0]
        data = listbox.get(index)
        parts = data.split('|')
        author_part = parts[0].strip()
        book_part = parts[1].strip()
        date_part = parts[2].strip()
        author = author_part.replace('Author: ', '')
        book = book_part.replace('Book: ', '')
        date = date_part.replace('Date Added: ', '')


        # Fill out the author and title fields
        author_entry.delete(0, tk.END)
        author_entry.insert(0, author)
        title_entry.delete(0, tk.END)
        title_entry.insert(0, book)
        start_date_picker.delete(0, tk.END)
        start_date_picker.insert(0, date)

        # Set the deck name as the book title and today's date
        today = datetime.date.today().strftime("%d-%m-%Y")
        deck_name = f"{book} {today}"
        deck_entry.delete(0, tk.END)
        deck_entry.insert(0, deck_name)


def create_deck(deck_name=None):
    # Generate a random number
    random_deck_id = random.randint(int(1e9), int(1e10))

    if deck_name is None:
        deck_name = "Deck_" + datetime.datetime.now().strftime("%Y-%m-%d")

    my_deck = genanki.Deck(random_deck_id, deck_name)

    return my_deck


def make_note(lang, eng, audio):    ## would need to be part of a larger function where lang, eng, and audio parameters are created
  return genanki.Note(
    model=my_model,
    fields=[lang, eng, audio]
  )


async def async_text_to_speech(text, output_file):
    async with sem:
        try:
            response = await async_client.audio.speech.create(
                model="tts-1",
                voice="nova",
                input=text
            )
            with open(output_file, 'wb') as f:
                f.write(response.content)  # Use response.content instead of iterating
            return True
        except Exception as e:
            print(f"Error creating audio for '{text}': {e}")
            return False


async def make_anki_cards(deck_name, media_list, author=None, title=None, start_date=None, end_date=None, ownpath=None):
    global is_running
    translation_generator = fetch_and_translate(author, title, start_date, end_date, ownpath)
    modified_rows = []

    # Translation phase
    total = 0
    for index, total, original, translation in translation_generator:
        if not is_running:
            break
        if index == 1:
            task_queue.put(("TOTAL", total, 0, total))

        task_queue.put(("TRANSLATE", original, translation, index, total))
        modified_rows.append((original, translation))

    if not is_running:
        return

    task_queue.put(("PHASE_COMPLETE", "Translation", total, total))

    # Text-to-speech phase
    async def process_row(index, row):
        if not is_running:
            return
        lang, eng = row
        file_name = f'{lang.replace(" ", "_")[:16]}.mp3'
        formatted_file_name = f'[sound:{file_name}]'
        media_list.append(file_name)

        success = await async_text_to_speech(lang, file_name)
        if not success:
            print(f"Failed to create audio for: {lang}")
            return

        note = make_note(lang, eng, formatted_file_name)
        deck_name.add_note(note)

        task_queue.put(("TTS", lang, eng, index, total))

    tasks = [process_row(i, row) for i, row in enumerate(modified_rows, 1)]
    await asyncio.gather(*tasks)

    if is_running:
        task_queue.put(("DONE", "DONE", total, total))



def run_asyncio_coroutine(coroutine):
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coroutine)



def bundle_anki_package(deck, media_files, output_filename=None):
    if output_filename is None:
        output_filename = f"{deck.name}.apkg"

    my_package = genanki.Package(deck)
    my_package.media_files = media_files
    my_package.write_to_file(output_filename)
    print(f"Anki package created: {output_filename}")  # Add this line for debugging

    return output_filename


def delete_media_files(media_files):
    for file_path in media_files:
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except OSError as e:
            print(f"Error deleting file {file_path}: {e.strerror}")


def cleanup_mp3_files():
    global media_list
    for file_path in media_list:
        try:
            os.remove(file_path)
            print(f"Deleted file: {file_path}")
        except OSError as e:
            print(f"Error deleting file {file_path}: {e.strerror}")
    media_list.clear()  # Clear the list after cleanup

def import_deck_to_anki(deck_path):
    abs_path = os.path.abspath(deck_path)
    url = 'http://localhost:8765'
    headers = {'Content-Type': 'application/json'}
    payload = {
        "action": "importPackage",
        "version": 6,
        "params": {
            "path": abs_path
        }
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print(f"Successfully imported deck: {deck_path}")
            return True
        else:
            print(f"Failed to import deck. Status code: {response.status_code}")
            print(f"Response content: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Error importing deck: {e}")
        return False

def post_processing(new_deck, deck_name):
    global is_running
    if not is_running:
        logging.info("Post-processing aborted as is_running is False")
        return
    try:
        logging.info("Starting to bundle Anki package")
        bundle_anki_package(new_deck, media_list)
        logging.info("Anki package bundled")
        deckpath = deck_name + ".apkg"
        logging.info(f"Attempting to import deck: {deckpath}")
        if import_deck_to_anki(deckpath):
            logging.info("Deck imported successfully")
            root.after(0, lambda: progress_label.config(text="Deck creation completed and imported to Anki!"))
        else:
            logging.warning("Deck import failed")
            root.after(0, lambda: progress_label.config(text="Deck creation completed, but import to Anki failed."))
    except Exception as e:
        logging.error(f"An error occurred during post-processing: {e}", exc_info=True)
        root.after(0, lambda: progress_label.config(text=f"Error during post-processing: {e}"))
    finally:
        cleanup_mp3_files()
        is_running = False
        root.after(0, lambda: abort_button.config(state=tk.DISABLED))
        root.after(0, lambda: deck_button.config(state=tk.NORMAL))
    logging.info("Post-processing completed")

def signal_handler(sig, frame):
    print("Process interrupted. Cleaning up...")
    cleanup_mp3_files()
    sys.exit(0)
def run_all():
    global new_deck, media_list, deck_name, processed_cards, current_progress, current_phase, is_running, loop
    is_running = True
    processed_cards = {}
    current_progress = 0
    current_phase = "Translation"
    media_list = []

    deck_name = deck_entry.get()
    author = author_entry.get()
    title = title_entry.get()
    start_date = start_date_picker.get()
    end_date = end_date_picker.get()

    listbox.delete(0, tk.END)
    progress_bar["value"] = 0
    progress_label.config(text="Creating cards...")

    new_deck = create_deck(deck_name)

    deck_button.config(state=tk.DISABLED)
    abort_button.config(state=tk.NORMAL)

    async def main():
        global is_running
        try:
            logging.info("Starting make_anki_cards")
            await make_anki_cards(new_deck, media_list, author, title, start_date, end_date)
            logging.info("Finished make_anki_cards")
            if is_running:
                logging.info("Starting post_processing")
                await asyncio.to_thread(post_processing, new_deck, deck_name)
                logging.info("Finished post_processing")
        except asyncio.CancelledError:
            logging.info("Operation was cancelled")
        except Exception as e:
            logging.error(f"An error occurred: {e}", exc_info=True)
        finally:
            is_running = False
            root.after(0, lambda: abort_button.config(state=tk.DISABLED))
            root.after(0, lambda: deck_button.config(state=tk.NORMAL))

    def run_async_main():
        global loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(main())
        finally:
            loop.close()

    executor.submit(run_async_main)
    logging.info("run_all completed")
def update_ui():
    global current_progress, current_phase
    try:
        while True:
            item = task_queue.get_nowait()

            if item[0] == "TOTAL":
                _, total_cards, _, _ = item
                progress_bar["maximum"] = total_cards
                progress_label.config(text=f"{current_phase} Progress: 0/{total_cards}")
            elif item[0] == "PHASE_COMPLETE":
                _, phase, _, _ = item
                listbox.delete(0, tk.END)  # Clear the listbox
                current_progress = 0
                processed_cards.clear()
                current_phase = "Text-to-Speech" if phase == "Translation" else "Complete"
                progress_label.config(text=f"{current_phase} Progress: 0/{total_cards}")
            elif item[0] == "DONE":
                _, _, total_cards, _ = item
                progress_bar["value"] = total_cards
                progress_label.config(text=f"Progress: {total_cards}/{total_cards}")
                processed_cards.clear()
            elif item[0] in ["TRANSLATE", "TTS"]:
                _, lang, eng, index, total_cards = item
                processed_cards[index] = (lang, eng)

                while current_progress + 1 in processed_cards:
                    current_progress += 1
                    lang, eng = processed_cards[current_progress]

                    listbox.insert(tk.END,
                                   f"{current_phase}: {lang[:50]}..." if len(lang) > 50 else f"{current_phase}: {lang}")
                    listbox.insert(tk.END, f"Translation: {eng[:50]}..." if len(eng) > 50 else f"Translation: {eng}")
                    listbox.insert(tk.END, "")  # Empty line for spacing
                    listbox.yview_moveto(1)  # Scroll to the bottom

                    progress_bar["value"] = current_progress
                    progress_label.config(text=f"{current_phase} Progress: {current_progress}/{total_cards}")

                for i in range(1, current_progress + 1):
                    processed_cards.pop(i, None)

            root.update_idletasks()
    except Empty:
        pass

    root.after(10, update_ui)


def abort_process():
    global is_running, executor
    logging.info("Abort process initiated")
    is_running = False
    cleanup_mp3_files()
    progress_label.config(text="Process aborted. Files cleaned up.")
    abort_button.config(state=tk.DISABLED)
    deck_button.config(state=tk.NORMAL)

    # Cancel all running tasks
    for task in asyncio.all_tasks(loop):
        task.cancel()

    # Shutdown the executor and create a new one
    executor.shutdown(wait=False)
    executor = ThreadPoolExecutor()
    logging.info("Abort process completed")
#
#     ## 1. Create new deck with its own name
#     deck = create_deck(args.deck_name)
#
#
#     # 1.1 Show first few rows to confirm
#     # Wait for user confirmation
# #def print_first_rows(author=None, title=None, start_date=None, end_date=None, ownpath=None, translate=False):
#
#     print_first_rows(args.author, args.title, args.start_date, args.end_date, args.own_path, translate=True)
#     input("Press Enter to continue or Ctrl+C to abort...")
#
#
#     ##2. package anki cards into deck and deck make media.
#     make_anki_cards(deck, media_list, args.author, args.title, args.start_date, args.end_date, args.own_path)
#
#     #3. Package media and deck together into anki package
#     bundle_anki_package(deck, media_list, args.file_name)
#
#
#     #4. delete audio files to reduce clutter
#     delete_media_files(media_list)
#
#     #5. optionally import to anki
#
#     if args.import_to_anki:
#         import_deck_to_anki(args.file_name)
#



# Create the main window
root = tk.Tk()
root.title("Kobo Book and Author Fetcher")

# Create a main frame to hold the sidebar and content
main_frame = ttk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True)

# Create a sidebar frame
sidebar_frame = ttk.Frame(main_frame, width=200, relief=tk.RAISED, borderwidth=1)
sidebar_frame.pack(fill=tk.Y, side=tk.LEFT, padx=10, pady=10)

# Create a content frame
content_frame = ttk.Frame(main_frame)
content_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=10, pady=10)



# Add widgets to the sidebar
ttk.Label(sidebar_frame, text="Deck Name").pack(pady=5)
deck_entry = ttk.Entry(sidebar_frame)
deck_entry.pack(fill=tk.X, padx=5, pady=5)

ttk.Label(sidebar_frame, text="Author:").pack(pady=5)
author_entry = ttk.Entry(sidebar_frame)
author_entry.pack(fill=tk.X, padx=5, pady=5)

ttk.Label(sidebar_frame, text="Book Title:").pack(pady=5)
title_entry = ttk.Entry(sidebar_frame)
title_entry.pack(fill=tk.X, padx=5, pady=5)

ttk.Label(sidebar_frame, text="Start Date:").pack(pady=5)
start_date_picker = DateEntry(sidebar_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
start_date_picker.pack(fill=tk.X, padx=5, pady=5)

ttk.Label(sidebar_frame, text="End Date:").pack(pady=5)
end_date_picker = DateEntry(sidebar_frame, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
end_date_picker.pack(fill=tk.X, padx=5, pady=5)

search_button = ttk.Button(sidebar_frame, text="Search Annotations", command=fetch_and_display_annotations)
search_button.pack(fill=tk.X, padx=5, pady=20)

deck_button = ttk.Button(sidebar_frame, text="Run", command=run_all)
deck_button.pack(fill=tk.X, padx=5, pady=20)

# Add widgets to the content frame
sort_frame = ttk.Frame(content_frame)
sort_frame.pack(fill=tk.X, pady=10)

sort_option = tk.StringVar(value='Author')
sort_menu = ttk.OptionMenu(sort_frame, sort_option, 'Author', 'Author', 'Book', 'Date Added')
sort_menu.pack(side=tk.LEFT, padx=5)

fetch_button = ttk.Button(sort_frame, text="Fetch Books & Authors", command=fetch_books_and_authors_with_sort)
fetch_button.pack(side=tk.LEFT, padx=5)

abort_button = ttk.Button(sidebar_frame, text="Abort", command=abort_process, state=tk.DISABLED)
abort_button.pack(fill=tk.X, padx=5, pady=20)

# Add a listbox to display the results
listbox = tk.Listbox(content_frame, width=100, height=20, font=("Courier", 16))
listbox.pack(fill=tk.BOTH, expand=True, pady=10)

progress_bar = ttk.Progressbar(content_frame, orient="horizontal", length=300, mode="determinate")
progress_bar.pack(pady=10)

progress_label = ttk.Label(content_frame, text="")
progress_label.pack(pady=5)

# Bind the listbox select event to the handler
listbox.bind('<Double-1>', on_listbox_select)

root.after(10, update_ui)
# Run the application

if __name__ == "__main__":
    try:
        root.mainloop()
    except Exception as e:
        logging.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
        cleanup_mp3_files()
    finally:
        logging.info("Application closed.")
        if 'loop' in globals() and loop.is_running():
            loop.close()
### Works!
        ## Todo: - see if this is fine as is or if it should be split up into a main/ functions/ constants organisation