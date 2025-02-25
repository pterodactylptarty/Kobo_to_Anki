import tkinter as tk
from tkinter import messagebox
import deepl
import datetime
import genanki
import os
from queue import Queue
import asyncio
import logging
from openai import AsyncOpenAI
from api_keys import openai_key, DeepL
from concurrent.futures import ThreadPoolExecutor
import appdirs
import sys
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
        self.use_tts = tk.BooleanVar(value=True)  # Add this to track TTS status

        self.async_client = None
        self.translator = None
        self.is_standalone = self._is_running_as_standalone()

        # Keep the existing CSS and model definition
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
        self.load_api_keys()

    def process_text_file(self, file_path):
        """Process a text file with words/phrases and yield translations"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            total_lines = len(lines)
            for index, original in enumerate(lines, 1):
                if not self.is_running:
                    break

                try:
                    # Translate the line
                    translation = self.translator.translate_text(original, target_lang="EN-US").text
                    yield index, total_lines, original, translation
                except Exception as e:
                    logging.error(f"Error translating line '{original}': {e}")
                    # Yield the original text as both source and translation if translation fails
                    yield index, total_lines, original, f"[Translation failed: {str(e)}]"

        except Exception as e:
            logging.error(f"Error processing text file: {e}")
            messagebox.showerror("Error", f"Failed to process text file: {str(e)}")
            yield 1, 1, "Error", f"Failed to process file: {str(e)}"
    def _is_running_as_standalone(self):
        return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

    def get_user_data_dir(self):
        if self.is_standalone:
            return appdirs.user_data_dir("KoboAnkiCreator", "DavidConforti")
        else:
            return os.path.dirname(os.path.abspath(__file__))

    def get_api_keys_path(self):
        return os.path.join(self.get_user_data_dir(), 'aaa_api_keys.json')
    def log_environment_info(self):
        logging.debug(f"Current working directory: {os.getcwd()}")
        logging.debug(f"__file__: {__file__}")
        logging.debug(f"sys.executable: {sys.executable}")
        if getattr(sys, 'frozen', False):
            logging.debug(f"sys._MEIPASS: {sys._MEIPASS}")
        logging.debug(f"API keys path: {self.get_api_keys_path()}")

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

        deepl_api_key = self.deepl_key_entry.get() or DeepL

        # Validate the required API key
        if not deepl_api_key:
            messagebox.showerror("API Error", "DeepL API key is required for translation.")
            self.is_running = False
            return

        # Only initialize OpenAI client if TTS is enabled
        if self.use_tts.get():
            openai_api_key = self.openai_key_entry.get() or openai_key
            if not openai_api_key:
                messagebox.showerror("API Error", "OpenAI API key is required for audio generation.")
                self.is_running = False
                return
            try:
                self.async_client = AsyncOpenAI(api_key=openai_api_key)
            except Exception as e:
                messagebox.showerror("API Error", f"Failed to initialize OpenAI client: {str(e)}")
                self.is_running = False
                return
        else:
            self.async_client = None  # No OpenAI client needed

        try:
            self.translator = deepl.Translator(deepl_api_key)
        except Exception as e:
            messagebox.showerror("API Error", f"Failed to initialize DeepL translator: {str(e)}")
            self.is_running = False
            return

        deck_name = self.deck_entry.get()

        # Update deck name if it's empty
        if not deck_name:
            if self.source_var.get() == "import" and self.import_path.get():
                # Use the filename as the deck name if importing a file
                file_name = os.path.basename(self.import_path.get())
                base_name = os.path.splitext(file_name)[0]
                deck_name = f"{base_name}_{datetime.datetime.now().strftime('%Y-%m-%d')}"
            else:
                deck_name = f"Deck_{datetime.datetime.now().strftime('%Y-%m-%d')}"

            self.deck_entry.delete(0, tk.END)
            self.deck_entry.insert(0, deck_name)

        # Update UI to indicate if audio is being generated
        source_text = "imported text" if self.source_var.get() == "import" else "Kobo annotations"
        phase_text = f"Creating cards from {source_text}" + (" with audio" if self.use_tts.get() else " without audio")
        self.listbox.delete(0, tk.END)
        self.progress_bar["value"] = 0
        self.progress_label.config(text=f"{phase_text}...")

        new_deck = self.create_deck(deck_name)

        self.deck_button.config(state=tk.DISABLED)
        self.abort_button.config(state=tk.NORMAL)

        async def main():
            try:
                logging.info("Starting make_cards")
                if self.source_var.get() == "import":
                    # Process imported text file
                    import_path = self.import_path.get()
                    if not import_path or not os.path.exists(import_path):
                        raise ValueError("No valid import file selected")

                    await self.make_anki_cards_from_generator(
                        new_deck,
                        self.media_list,
                        self.process_text_file(import_path)
                    )
                else:
                    # Process Kobo annotations
                    author = self.author_entry.get()
                    title = self.title_entry.get()
                    start_date = self.start_date_picker.get()
                    end_date = self.end_date_picker.get()

                    await self.make_anki_cards(new_deck, self.media_list, author, title, start_date, end_date)

                logging.info("Finished making cards")

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

    async def make_anki_cards_from_generator(self, deck_name, media_list, translation_generator):
        """
        Creates Anki cards from any generator that yields (index, total, original, translation)
        This is used for both Kobo annotations and imported text files
        """
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

            if self.use_tts.get() and self.async_client:
                # Only create audio if TTS is enabled and OpenAI client is available
                file_name = f'{lang.replace(" ", "_")[:16]}.mp3'
                formatted_file_name = f'[sound:{file_name}]'
                media_list.append(file_name)

                success = await self.async_text_to_speech(lang, file_name, sem)
                if success:
                    note = self.make_note(lang, eng, formatted_file_name)
                else:
                    # Create note without audio if TTS failed
                    note = self.make_note(lang, eng)
            else:
                # Create note without audio
                note = self.make_note(lang, eng)

            deck_name.add_note(note)

            # Update the task phase description based on whether TTS is enabled
            task_phase = "TTS" if self.use_tts.get() else "Processing"
            self.task_queue.put((task_phase, lang, eng, index, total))

        tasks = [process_row(i, row) for i, row in enumerate(modified_rows, 1)]
        await asyncio.gather(*tasks)

        if self.is_running:
            self.task_queue.put(("DONE", "DONE", total, total))

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
