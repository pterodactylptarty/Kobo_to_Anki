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

class UI:
    def setup_ui(self):
        self.root.title("Kobo Book and Author Fetcher")

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        sidebar_frame = ttk.Frame(main_frame, width=200, relief=tk.RAISED, borderwidth=1)
        sidebar_frame.pack(fill=tk.Y, side=tk.LEFT, padx=10, pady=10)

        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=10, pady=10)

        # Top frame for API keys and sort options
        top_frame = ttk.Frame(content_frame)
        top_frame.pack(fill=tk.X, pady=10)

        # API key entries and save button
        api_frame = ttk.Frame(top_frame)
        api_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)

        ttk.Label(api_frame, text="OpenAI API Key:").pack(side=tk.LEFT, padx=5)
        self.openai_key_entry = ttk.Entry(api_frame, width=20, show="*")
        self.openai_key_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(api_frame, text="DeepL API Key:").pack(side=tk.LEFT, padx=5)
        self.deepl_key_entry = ttk.Entry(api_frame, width=20, show="*")
        self.deepl_key_entry.pack(side=tk.LEFT, padx=5)

        self.save_keys_button = ttk.Button(api_frame, text="Save API Keys", command=self.save_api_keys)
        self.save_keys_button.pack(side=tk.LEFT, padx=5)

        # Sort options
        sort_frame = ttk.Frame(top_frame)
        sort_frame.pack(side=tk.LEFT, padx=10)

        self.sort_option = tk.StringVar(value='Author')
        sort_menu = ttk.OptionMenu(sort_frame, self.sort_option, 'Author', 'Author', 'Book', 'Date Added')
        sort_menu.pack(side=tk.LEFT, padx=5)

        fetch_button = ttk.Button(sort_frame, text="Fetch Books & Authors",
                                  command=self.fetch_books_and_authors_with_sort)
        fetch_button.pack(side=tk.LEFT, padx=5)

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

        self.search_button = ttk.Button(sidebar_frame, text="Search Annotations",
                                        command=self.fetch_and_display_annotations)
        self.search_button.pack(fill=tk.X, padx=5, pady=20)

        self.deck_button = ttk.Button(sidebar_frame, text="Run", command=self.run_all)
        self.deck_button.pack(fill=tk.X, padx=5, pady=20)

        self.abort_button = ttk.Button(sidebar_frame, text="Abort", command=self.abort_process, state=tk.DISABLED)
        self.abort_button.pack(fill=tk.X, padx=5, pady=20)

        # Listbox
        self.listbox = tk.Listbox(content_frame, width=100, height=20, font=("Courier", 16))
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=10)

        self.progress_bar = ttk.Progressbar(content_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        self.progress_label = ttk.Label(content_frame, text="")
        self.progress_label.pack(pady=5)

        self.listbox.bind('<Double-1>', self.on_listbox_select)
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

    def save_api_keys(self):
        openai_key = self.openai_key_entry.get().strip()
        deepl_key = self.deepl_key_entry.get().strip()

        if not openai_key or not deepl_key:
            messagebox.showerror("Error", "Both API keys must be provided.")
            return

        # Update this line to point to the correct api_keys.py file
        api_keys_path = os.path.join(os.path.dirname(__file__), 'api_keys.py')

        with open(api_keys_path, 'w') as f:
            f.write(f"openai_key = '{openai_key}'\n")
            f.write(f"DeepL = '{deepl_key}'\n")

        messagebox.showinfo("Success", "API keys have been saved successfully.")

        # Update the current session with new keys
        self.openai_key = openai_key
        self.deepl_key = deepl_key

    def load_api_keys(self):
        api_keys_path = os.path.join(os.path.dirname(__file__), 'api_keys.py')

        if os.path.exists(api_keys_path):
            with open(api_keys_path, 'r') as f:
                exec(f.read(), globals())

            self.openai_key = globals().get('openai_key', '')
            self.deepl_key = globals().get('DeepL', '')

            # Populate the entry fields
            self.openai_key_entry.insert(0, self.openai_key)
            self.deepl_key_entry.insert(0, self.deepl_key)
