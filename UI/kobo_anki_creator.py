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
from ui import UI
from kobo_utils import KoboUtils
from anki_utils import AnkiUtils


class KoboAnkiCreator(UI, KoboUtils, AnkiUtils):
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

    def run_asyncio_coroutine(self, coroutine):
        asyncio.set_event_loop(asyncio.new_event_loop())
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(coroutine)

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
