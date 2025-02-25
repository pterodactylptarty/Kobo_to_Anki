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
import appdirs
import tempfile
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

    def get_anki_deck_dir(self):
        if self.is_standalone:
            base_dir = appdirs.user_data_dir("KoboAnkiCreator", "Conforti")
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        deck_dir = os.path.join(base_dir, "Decks")
        os.makedirs(deck_dir, exist_ok=True)
        logging.info(f"Anki deck directory: {deck_dir}")
        return deck_dir
    def get_anki_deck_path(self, deck_name):
        return os.path.join(self.get_anki_deck_dir(), f"{deck_name}.apkg")

    def get_media_dir(self):
        if self.is_standalone:
            base_dir = appdirs.user_data_dir("KoboAnkiCreator", "YourName_HobbyProjects")
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        media_dir = os.path.join(base_dir, "media")
        os.makedirs(media_dir, exist_ok=True)
        return media_dir

    def create_deck(self, deck_name=None):
        random_deck_id = random.randint(int(1e9), int(1e10))
        if deck_name is None:
            deck_name = "Deck_" + datetime.datetime.now().strftime("%Y-%m-%d")
        return genanki.Deck(random_deck_id, deck_name)

    def make_note(self, lang, eng, audio=None):
        """Create a note with or without audio"""
        if audio:
            # With audio
            return genanki.Note(
                model=self.my_model,
                fields=[lang, eng, audio]
            )
        else:
            # Without audio - use empty string for the audio field
            return genanki.Note(
                model=self.my_model,
                fields=[lang, eng, '']
            )

    async def async_text_to_speech(self, text, output_file, sem):
        async with sem:
            try:
                response = await self.async_client.audio.speech.create(
                    model="tts-1",
                    voice="nova",
                    input=text
                )
                full_output_path = os.path.join(self.get_media_dir(), output_file)
                with open(full_output_path, 'wb') as f:
                    f.write(response.content)
                return True
            except Exception as e:
                print(f"Error creating audio for '{text}': {e}")
                return False

    async def make_anki_cards(self, deck_name, media_list, author=None, title=None, start_date=None, end_date=None,
                              ownpath=None):
        """Creates Anki cards from Kobo annotations"""
        # Just use the generic method with the Kobo-specific generator
        translation_generator = self.fetch_and_translate(author, title, start_date, end_date, ownpath)
        await self.make_anki_cards_from_generator(deck_name, media_list, translation_generator)

    def bundle_anki_package(self, deck, media_files, deck_name):
        output_filename = self.get_anki_deck_path(deck_name)

        my_package = genanki.Package(deck)
        my_package.media_files = [os.path.join(self.get_media_dir(), file) for file in media_files]

        try:
            my_package.write_to_file(output_filename)
            logging.info(f"Anki package created successfully: {output_filename}")
        except Exception as e:
            logging.error(f"Failed to create Anki package: {e}")
            raise

        return output_filename

    def delete_media_files(self, media_files):
        for file_path in media_files:
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except OSError as e:
                print(f"Error deleting file {file_path}: {e.strerror}")



    def cleanup_mp3_files(self):
        media_dir = os.path.join(appdirs.user_data_dir("KoboAnkiCreator", "Conforti"), "media")
        for file_name in os.listdir(media_dir):
            if file_name.endswith('.mp3'):
                file_path = os.path.join(media_dir, file_name)
                try:
                    os.remove(file_path)
                    logging.info(f"Deleted file: {file_path}")
                except OSError as e:
                    logging.error(f"Error deleting file {file_path}: {e}")
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
            deck_path = self.bundle_anki_package(new_deck, self.media_list, deck_name)
            logging.info(f"Anki package bundled at {deck_path}")

            # Clean up media files after the package is created
            self.cleanup_mp3_files()

            import_success = self.import_deck_to_anki(deck_path)
            if import_success:
                logging.info("Deck imported successfully")
                message = f"Deck creation completed and imported to Anki!\nSaved at: {deck_path}"
            else:
                logging.warning("Deck import failed")
                message = f"Deck creation completed, but import to Anki failed.\nDeck saved at: {deck_path}"

            self.root.after(0, lambda msg=message: self.progress_label.config(text=msg))
        except Exception as e:
            logging.error(f"An error occurred during post-processing: {e}", exc_info=True)
            error_message = f"Error during post-processing: {str(e)}"
            self.root.after(0, lambda msg=error_message: self.progress_label.config(text=msg))
        finally:
            self.cleanup_mp3_files()
            self.is_running = False
            self.root.after(0, lambda: self.abort_button.config(state=tk.DISABLED))
            self.root.after(0, lambda: self.deck_button.config(state=tk.NORMAL))
            self.root.after(0, self.update_ui)
        logging.info("Post-processing completed")