from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import DateEntry
import deepl
import random
import datetime
import genanki
import requests
import os
from queue import Queue, Empty
import asyncio
import logging
from openai import AsyncOpenAI
from typing import Optional
from api_keys import openai_key, DeepL
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import json
import shutil
import subprocess

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class KoboAnkiCreator:
    def __init__(self):
        self.root = tk.Tk()
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.task_queue = Queue()
        self.error_queue = Queue()
        self.is_running = False
        self.executor = ThreadPoolExecutor()
        self.media_list = []
        self.processed_cards = {}
        self.current_progress = 0
        self.current_phase = "Translation"
        self.total_cards = 0

        self.async_client = None
        self.translator = None

        self.my_css = """
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

        self.my_model = genanki.Model(
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
            css=self.my_css
        )

        self.setup_ui()

    def setup_ui(self):
        self.root.title("Kobo Book and Author Fetcher")

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar_frame = ttk.Frame(main_frame, width=200, relief=tk.RAISED, borderwidth=1)
        sidebar_frame.pack(fill=tk.Y, side=tk.LEFT, padx=10, pady=10)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=10, pady=10)

        # Sidebar widgets
        ttk.Label(sidebar_frame, text="Deck Name").pack(pady=5)
        self.deck_entry = ttk.Entry(sidebar_frame)
        self.deck_entry.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(sidebar_frame, text="Author:").pack(pady=5)
        self.author_entry = ttk.Entry(sidebar_frame)
        self.author_entry.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(sidebar_frame, text="Book Title:").pack(pady=5)
        self.title_entry = ttk.Entry(sidebar_frame)
        self.title_entry.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(sidebar_frame, text="Start Date:").pack(pady=5)
        self.start_date_picker = DateEntry(sidebar_frame, width=12, background='darkblue', foreground='white',
                                           borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_picker.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(sidebar_frame, text="End Date:").pack(pady=5)
        self.end_date_picker = DateEntry(sidebar_frame, width=12, background='darkblue', foreground='white',
                                         borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_picker.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(sidebar_frame, text="OpenAI API Key:").pack(pady=5)
        self.openai_key_entry = ttk.Entry(sidebar_frame)
        self.openai_key_entry.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(sidebar_frame, text="DeepL API Key:").pack(pady=5)
        self.deepl_key_entry = ttk.Entry(sidebar_frame)
        self.deepl_key_entry.pack(fill=tk.X, padx=5, pady=5)

        self.search_button = ttk.Button(sidebar_frame, text="Search Annotations",
                                        command=self.fetch_and_display_annotations)
        self.search_button.pack(fill=tk.X, padx=5, pady=20)

        self.deck_button = ttk.Button(sidebar_frame, text="Run", command=self.run_all)
        self.deck_button.pack(fill=tk.X, padx=5, pady=20)

        self.abort_button = ttk.Button(sidebar_frame, text="Abort", command=self.abort_process, state=tk.DISABLED)
        self.abort_button.pack(fill=tk.X, padx=5, pady=20)

        # Content frame widgets
        sort_frame = ttk.Frame(content_frame)
        sort_frame.pack(fill=tk.X, pady=10)

        self.sort_option = tk.StringVar(value='Author')
        sort_menu = ttk.OptionMenu(sort_frame, self.sort_option, 'Author', 'Author', 'Book', 'Date Added')
        sort_menu.pack(side=tk.LEFT, padx=5)

        fetch_button = ttk.Button(sort_frame, text="Fetch Books & Authors",
                                  command=self.fetch_books_and_authors_with_sort)
        fetch_button.pack(side=tk.LEFT, padx=5)

        self.listbox = tk.Listbox(content_frame, width=100, height=20, font=("Courier", 16))
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=10)

        self.progress_bar = ttk.Progressbar(content_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        self.progress_label = ttk.Label(content_frame, text="")
        self.progress_label.pack(pady=5)

        self.listbox.bind('<Double-1>', self.on_listbox_select)

    def get_kobo_mountpoint(self, label: str = 'KOBOeReader') -> Optional[Path]:
        has_lsblk = shutil.which('lsblk')
        if has_lsblk:  # on Linux
            xxx = subprocess.check_output(['lsblk', '-f', '--json']).decode('utf8')
            jj = json.loads(xxx)
            devices = [d for d in jj['blockdevices'] if d.get('label', None) == label]
            kobos = []
            for d in devices:
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

    def fetch_books_and_authors(self, sort_by='Author', ownpath=None):
        if ownpath is None:
            kobo_path = self.get_kobo_mountpoint()
            if kobo_path is None:
                messagebox.showerror("Error", "No Kobo device detected")
                return
            conn = sqlite3.connect(kobo_path / '.kobo' / 'KoboReader.sqlite')
        else:
            conn = sqlite3.connect(ownpath)
        cursor = conn.cursor()

        if sort_by == 'Author':
            sort_column = 'Content.Attribution'
        elif sort_by == 'Book':
            sort_column = 'Content.Title'
        elif sort_by == 'Date Added':
            sort_column = 'Content.___SyncTime'

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

        self.listbox.delete(0, tk.END)

        header = f"{'Author':<30} | {'Book':<40} | {'Date Added':<20}"
        self.listbox.insert(tk.END, header)
        self.listbox.insert(tk.END, "-" * len(header))

        for result in results:
            author = result[1][:28] + '..' if len(result[1]) > 30 else result[1]
            book = result[0][:38] + '..' if len(result[0]) > 40 else result[0]
            date_added = result[2][:19]

            formatted_line = f"{author:<30} | {book:<40} | {date_added:<20}"
            self.listbox.insert(tk.END, formatted_line)

        self.listbox.config(font=("Courier", 16))

    def fetch_annotations(self, author=None, title=None, start_date=None, end_date=None, ownpath=None):
        if ownpath is None:
            conn = sqlite3.connect(self.get_kobo_mountpoint() / '.kobo' / 'KoboReader.sqlite')
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

    def fetch_and_translate(self, author=None, title=None, start_date=None, end_date=None, ownpath=None):
        if ownpath is None:
            conn = sqlite3.connect(self.get_kobo_mountpoint() / '.kobo' / 'KoboReader.sqlite')
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
            translation = self.translator.translate_text(original_text, target_lang="EN-US").text

            modified_row = result[:1] + (translation,) + result[1:]
            modified_rows.append(modified_row)

            yield index, len(results), original_text, translation

        return modified_rows

    def display_annotations(self, annotations):
        self.listbox.delete(0, tk.END)

        if not annotations:
            self.listbox.insert(tk.END, "No annotations found.")
            return

        headers = ["Text", "Date Created"]
        self.listbox.insert(tk.END, f"{'Text':<80} | {'Date Created':<20}")
        self.listbox.insert(tk.END, "-" * 102)

        for annotation in annotations:
            text = annotation[0]
            date_created = annotation[2]

            if len(text) > 77:
                formatted_text = text[:77] + "..."
            else:
                formatted_text = text.ljust(80)

            formatted_date = date_created[:19]

            formatted_line = f"{formatted_text} | {formatted_date:<20}"
            self.listbox.insert(tk.END, formatted_line)

        self.listbox.config(width=102)

    def fetch_and_display_annotations(self):
        author = self.author_entry.get()
        title = self.title_entry.get()
        start_date = self.start_date_picker.get_date().strftime("%Y-%m-%d") if self.start_date_picker.get() else None
        end_date = self.end_date_picker.get_date().strftime("%Y-%m-%d") if self.end_date_picker.get() else None

        annotations = self.fetch_annotations(author, title, start_date, end_date)
        self.display_annotations(annotations)

    def fetch_books_and_authors_with_sort(self):
        sort_by = self.sort_option.get()
        self.fetch_books_and_authors(sort_by)

    def on_listbox_select(self, event):
        selection = self.listbox.curselection()
        if selection:
            index = selection[0]
            data = self.listbox.get(index)
            parts = data.split('|')
            author_part = parts[0].strip()
            book_part = parts[1].strip()
            date_part = parts[2].strip()
            author = author_part.replace('Author: ', '')
            book = book_part.replace('Book: ', '')
            date = date_part.replace('Date Added: ', '')

            self.author_entry.delete(0, tk.END)
            self.author_entry.insert(0, author)
            self.title_entry.delete(0, tk.END)
            self.title_entry.insert(0, book)
            self.start_date_picker.delete(0, tk.END)
            self.start_date_picker.insert(0, date)

            today = datetime.date.today().strftime("%d-%m-%Y")
            deck_name = f"{book} {today}"
            self.deck_entry.delete(0, tk.END)
            self.deck_entry.insert(0, deck_name)

    def create_deck(self, deck_name=None):
        random_deck_id = random.randint(int(1e9), int(1e10))
        if deck_name is None:
            deck_name = "Deck_" + datetime.datetime.now().strftime("%Y-%m-%d")
        return genanki.Deck(random_deck_id, deck_name)

    def make_note(self, lang, eng, audio):
        return genanki.Note(
            model=self.my_model,
            fields=[lang, eng, audio]
        )

    async def async_text_to_speech(self, text, output_file, sem):
        async with sem:
            try:
                response = await self.async_client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=text
                )
                with open(output_file, 'wb') as f:
                    f.write(response.content)
                return True
            except Exception as e:
                print(f"Error creating audio for '{text}': {e}")
                return False

    async def make_anki_cards(self, deck_name, media_list, author=None, title=None, start_date=None, end_date=None,
                              ownpath=None):
        translation_generator = self.fetch_and_translate(author, title, start_date, end_date, ownpath)
        modified_rows = []

        sem = asyncio.Semaphore(2)

        total = 0
        for index, total, original, translation in translation_generator:
            if not self.is_running:
                break
            if index == 1:
                self.task_queue.put(("TOTAL", total, 0, total))

            self.task_queue.put(("TRANSLATE", original, translation, index, total))
            modified_rows.append((original, translation))

        if not self.is_running:
            return

        self.task_queue.put(("PHASE_COMPLETE", "Translation", total, total))

        async def process_row(index, row):
            if not self.is_running:
                return
            lang, eng = row
            file_name = f'{lang.replace(" ", "_")[:16]}.mp3'
            formatted_file_name = f'[sound:{file_name}]'
            media_list.append(file_name)

            success = await self.async_text_to_speech(lang, file_name, sem)
            if not success:
                print(f"Failed to create audio for: {lang}")
                return

            note = self.make_note(lang, eng, formatted_file_name)
            deck_name.add_note(note)

            self.task_queue.put(("TTS", lang, eng, index, total))

        tasks = [process_row(i, row) for i, row in enumerate(modified_rows, 1)]
        await asyncio.gather(*tasks)

        if self.is_running:
            self.task_queue.put(("DONE", "DONE", total, total))

    def run_asyncio_coroutine(self, coroutine):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coroutine)

    def bundle_anki_package(self, deck, media_files, output_filename=None):
        if output_filename is None:
            output_filename = f"{deck.name}.apkg"

        my_package = genanki.Package(deck)
        my_package.media_files = media_files
        my_package.write_to_file(output_filename)
        print(f"Anki package created: {output_filename}")

        return output_filename

    def delete_media_files(self, media_files):
        for file_path in media_files:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except OSError as e:
                print(f"Error deleting file {file_path}: {e.strerror}")

    def cleanup_mp3_files(self):
        for file_path in self.media_list:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except OSError as e:
                print(f"Error deleting file {file_path}: {e.strerror}")
        self.media_list.clear()

    def import_deck_to_anki(self, deck_path):
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

    def post_processing(self, new_deck, deck_name):
        if not self.is_running:
            logging.info("Post-processing aborted as is_running is False")
            return
        try:
            logging.info("Starting to bundle Anki package")
            self.bundle_anki_package(new_deck, self.media_list)
            logging.info("Anki package bundled")
            deckpath = deck_name + ".apkg"
            logging.info(f"Attempting to import deck: {deckpath}")
            if self.import_deck_to_anki(deckpath):
                logging.info("Deck imported successfully")
                self.root.after(0, lambda: self.progress_label.config(
                    text="Deck creation completed and imported to Anki!"))
            else:
                logging.warning("Deck import failed")
                self.root.after(0, lambda: self.progress_label.config(
                    text="Deck creation completed, but import to Anki failed."))
        except Exception as e:
            logging.error(f"An error occurred during post-processing: {e}", exc_info=True)
            self.root.after(0, lambda: self.progress_label.config(text=f"Error during post-processing: {e}"))
        finally:
            self.cleanup_mp3_files()
            self.is_running = False
            self.root.after(0, lambda: self.abort_button.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.deck_button.config(state=tk.NORMAL))
            self.root.after(0, self.update_ui)
        logging.info("Post-processing completed")

    def run_all(self):
        self.is_running = True
        self.processed_cards = {}
        self.current_progress = 0
        self.current_phase = "Translation"
        self.media_list = []

        openai_api_key = self.openai_key_entry.get() or openai_key
        deepl_api_key = self.deepl_key_entry.get() or DeepL

        try:
            self.async_client = AsyncOpenAI(api_key=openai_api_key)
            self.translator = deepl.Translator(deepl_api_key)
        except Exception as e:
            messagebox.showerror("API Error", f"Failed to initialize API clients: {str(e)}")
            self.is_running = False
            return

        deck_name = self.deck_entry.get()
        author = self.author_entry.get()
        title = self.title_entry.get()
        start_date = self.start_date_picker.get()
        end_date = self.end_date_picker.get()

        self.listbox.delete(0, tk.END)
        self.progress_bar["value"] = 0
        self.progress_label.config(text="Creating cards...")

        new_deck = self.create_deck(deck_name)

        self.deck_button.config(state=tk.DISABLED)
        self.abort_button.config(state=tk.NORMAL)

        async def main():
            try:
                logging.info("Starting make_anki_cards")
                await self.make_anki_cards(new_deck, self.media_list, author, title, start_date, end_date)
                logging.info("Finished make_anki_cards")
                if self.is_running:
                    logging.info("Starting post_processing")
                    await asyncio.to_thread(self.post_processing, new_deck, deck_name)
                    logging.info("Finished post_processing")
            except asyncio.CancelledError:
                logging.info("Operation was cancelled")
            except Exception as e:
                logging.error(f"An error occurred: {e}", exc_info=True)
                self.error_queue.put(str(e))
            finally:
                self.is_running = False
                self.root.after(0, lambda: self.abort_button.config(state=tk.DISABLED))
                self.root.after(0, lambda: self.deck_button.config(state=tk.NORMAL))

        def run_async_main():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(main())
            finally:
                loop.close()

        self.executor.submit(run_async_main)
        self.root.after(100, self.check_error_queue)
        self.root.after(100, self.update_ui)
        logging.info("run_all completed")

    def check_error_queue(self):
        try:
            error_message = self.error_queue.get_nowait()
            messagebox.showerror("Error", f"An error occurred: {error_message}")
        except Empty:
            if self.is_running:
                self.root.after(100, self.check_error_queue)

    def update_ui(self):
        try:
            while True:
                item = self.task_queue.get_nowait()

                if item[0] == "TOTAL":
                    _, self.total_cards, _, _ = item
                    self.progress_bar["maximum"] = self.total_cards
                    self.progress_label.config(text=f"{self.current_phase} Progress: 0/{self.total_cards}")
                elif item[0] == "PHASE_COMPLETE":
                    _, phase, _, _ = item
                    self.listbox.delete(0, tk.END)
                    self.current_progress = 0
                    self.processed_cards.clear()
                    self.current_phase = "Text-to-Speech" if phase == "Translation" else "Complete"
                    self.progress_label.config(text=f"{self.current_phase} Progress: 0/{self.total_cards}")
                elif item[0] == "DONE":
                    _, _, self.total_cards, _ = item
                    self.progress_bar["value"] = self.total_cards
                    self.progress_label.config(text=f"Progress: {self.total_cards}/{self.total_cards}")
                    self.processed_cards.clear()
                elif item[0] in ["TRANSLATE", "TTS"]:
                    _, lang, eng, index, self.total_cards = item
                    self.processed_cards[index] = (lang, eng)

                    while self.current_progress + 1 in self.processed_cards:
                        self.current_progress += 1
                        lang, eng = self.processed_cards[self.current_progress]

                        self.listbox.insert(tk.END,
                                            f"{self.current_phase}: {lang[:50]}..." if len(
                                                lang) > 50 else f"{self.current_phase}: {lang}")
                        self.listbox.insert(tk.END,
                                            f"Translation: {eng[:50]}..." if len(eng) > 50 else f"Translation: {eng}")
                        self.listbox.insert(tk.END, "")
                        self.listbox.yview_moveto(1)

                        self.progress_bar["value"] = self.current_progress
                        self.progress_label.config(
                            text=f"{self.current_phase} Progress: {self.current_progress}/{self.total_cards}")

                    for i in range(1, self.current_progress + 1):
                        self.processed_cards.pop(i, None)

                self.root.update_idletasks()
        except Empty:
            pass

        try:
            error_message = self.error_queue.get_nowait()
            messagebox.showerror("Error", f"An error occurred: {error_message}")
            self.is_running = False
            self.abort_button.config(state=tk.DISABLED)
            self.deck_button.config(state=tk.NORMAL)
        except Empty:
            pass

        if self.is_running:
            self.root.after(100, self.update_ui)
        else:
            current_text = self.progress_label.cget("text")
            if "Progress:" in current_text and not current_text.startswith("Deck creation completed"):
                self.progress_label.config(text="Deck creation completed. Check for import status.")

    def abort_process(self):
        logging.info("Abort process initiated")
        self.is_running = False
        self.cleanup_mp3_files()
        self.progress_label.config(text="Process aborted. Files cleaned up.")
        self.abort_button.config(state=tk.DISABLED)
        self.deck_button.config(state=tk.NORMAL)

        for task in asyncio.all_tasks(self.loop):
            task.cancel()

        self.executor.shutdown(wait=False)
        self.executor = ThreadPoolExecutor()
        logging.info("Abort process completed")

    def run(self):
        self.root.after(10, self.update_ui)
        self.root.mainloop()


if __name__ == "__main__":
    app = KoboAnkiCreator()
    try:
        app.run()
    except Exception as e:
        logging.error(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
        app.cleanup_mp3_files()
    finally:
        logging.info("Application closed.")
        if app.loop.is_running():
            app.loop.close()