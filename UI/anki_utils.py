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

class AnkiUtils:

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

    async def make_anki_cards(self, deck_name, media_list, author=None, title=None, start_date=None, end_date=None, ownpath=None):
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
