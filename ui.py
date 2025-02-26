import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import DateEntry
import datetime
from datetime import timedelta
import os
from queue import Empty
import json
import sys


def get_api_keys_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.join(sys._MEIPASS, '', 'api_keys.py')
    else:
        # Running in a normal Python environment
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api_keys.py')
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

        self.use_tts = tk.BooleanVar(value=False)
        self.tts_checkbox = ttk.Checkbutton(api_frame, text="Generate Audio (requires OpenAI API)",
                                            variable=self.use_tts,
                                            command=self.toggle_openai_entry)
        self.tts_checkbox.pack(side=tk.LEFT, padx=5)

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

        # Sidebar widgets - using a specific pack order

        # 1. Deck Name at the top
        ttk.Label(sidebar_frame, text="Deck Name").pack(pady=5)
        self.deck_entry = ttk.Entry(sidebar_frame)
        self.deck_entry.pack(fill=tk.X, padx=5, pady=5)

        # 2. Kobo-specific fields
        self.kobo_frame = ttk.LabelFrame(sidebar_frame, text="Kobo Annotations")
        self.kobo_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.kobo_frame, text="Author:").pack(pady=5)
        self.author_entry = ttk.Entry(self.kobo_frame)
        self.author_entry.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.kobo_frame, text="Book Title:").pack(pady=5)
        self.title_entry = ttk.Entry(self.kobo_frame)
        self.title_entry.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.kobo_frame, text="Start Date:").pack(pady=5)
        self.start_date_picker = DateEntry(self.kobo_frame, width=12, background='darkblue', foreground='white',
                                           borderwidth=2, date_pattern='yyyy-mm-dd')
        self.start_date_picker.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(self.kobo_frame, text="End Date:").pack(pady=5)
        self.end_date_picker = DateEntry(self.kobo_frame, width=12, background='darkblue', foreground='white',
                                         borderwidth=2, date_pattern='yyyy-mm-dd')
        self.end_date_picker.pack(fill=tk.X, padx=5, pady=5)

        self.search_button = ttk.Button(self.kobo_frame, text="Search Annotations",
                                        command=self.fetch_and_display_annotations)
        self.search_button.pack(fill=tk.X, padx=5, pady=5)



        # 3. Text file import frame
        self.import_frame = ttk.LabelFrame(sidebar_frame, text="Text File Import")
        self.import_frame.pack(fill=tk.X, padx=5, pady=5)

        self.import_path = tk.StringVar()
        self.import_entry = ttk.Entry(self.import_frame, textvariable=self.import_path, state='readonly')
        self.import_entry.pack(fill=tk.X, padx=5, pady=5)

        import_buttons_frame = ttk.Frame(self.import_frame)
        import_buttons_frame.pack(fill=tk.X, padx=5, pady=5)

        import_button = ttk.Button(import_buttons_frame, text="Browse...", command=self.browse_text_file)
        import_button.pack(side=tk.LEFT, padx=5)

        clear_button = ttk.Button(import_buttons_frame, text="Clear", command=self.clear_import)
        clear_button.pack(side=tk.RIGHT, padx=5)

        # 4. Source selection - now placed right before the action buttons
        source_frame = ttk.LabelFrame(sidebar_frame, text="Source Selection")
        source_frame.pack(fill=tk.X, padx=5, pady=10)

        self.source_var = tk.StringVar(value="kobo")
        ttk.Radiobutton(source_frame, text="Kobo Annotations", variable=self.source_var,
                        value="kobo", command=self.toggle_source).pack(anchor=tk.W, padx=5, pady=2)
        ttk.Radiobutton(source_frame, text="Imported Text File", variable=self.source_var,
                        value="import", command=self.toggle_source).pack(anchor=tk.W, padx=5, pady=2)

        # 5. Action buttons - now at the bottom
        action_frame = ttk.Frame(sidebar_frame)
        action_frame.pack(fill=tk.X, padx=5, pady=10)

        self.deck_button = ttk.Button(action_frame, text="Run", command=self.run_all)
        self.deck_button.pack(fill=tk.X, pady=5)

        self.abort_button = ttk.Button(action_frame, text="Abort", command=self.abort_process, state=tk.DISABLED)
        self.abort_button.pack(fill=tk.X, pady=5)

        self.open_dir_button = ttk.Button(action_frame, text="Open Deck Folder", command=self.open_deck_directory)
        self.open_dir_button.pack(fill=tk.X, pady=5)

        # Listbox in the main content area
        self.listbox = tk.Listbox(content_frame, width=100, height=20, font=("Courier", 16))
        self.listbox.pack(fill=tk.BOTH, expand=True, pady=10)

        self.progress_bar = ttk.Progressbar(content_frame, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        self.progress_label = ttk.Label(content_frame, text="")
        self.progress_label.pack(pady=5)

        self.listbox.bind('<Double-1>', self.on_listbox_select)

        # Set up the initial state
        self.toggle_source()



    def toggle_source(self):
        """Enable/disable UI elements based on the selected source"""
        if self.source_var.get() == "kobo":
            # Enable Kobo-related fields
            for child in self.kobo_frame.winfo_children():
                if isinstance(child, (ttk.Entry, DateEntry, ttk.Button)):
                    child.config(state="normal")
            self.kobo_frame.config(style='')
            self.import_frame.config(style='Dim.TLabelframe')
        else:
            # Disable Kobo-related fields
            for child in self.kobo_frame.winfo_children():
                if isinstance(child, (ttk.Entry, DateEntry, ttk.Button)):
                    child.config(state="disabled")
            self.kobo_frame.config(style='Dim.TLabelframe')
            self.import_frame.config(style='')

    def browse_text_file(self):
        """Open file dialog to select a text file"""
        file_path = filedialog.askopenfilename(
            title="Select Text File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if file_path:
            self.import_path.set(file_path)
            # If a file is selected, automatically switch to import mode
            self.source_var.set("import")
            self.toggle_source()

    def clear_import(self):
        """Clear the import file path"""
        self.import_path.set("")

    def toggle_openai_entry(self):
        """Enable or disable the OpenAI API key entry based on checkbox state"""
        if self.use_tts.get():
            self.openai_key_entry.config(state="normal")
        else:
            self.openai_key_entry.config(state="disabled")
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

                    # Update phase label based on TTS setting
                    if phase == "Translation":
                        self.current_phase = "Text-to-Speech" if self.use_tts.get() else "Processing Cards"
                    else:
                        self.current_phase = "Complete"

                    self.progress_label.config(text=f"{self.current_phase} Progress: 0/{self.total_cards}")

                # Rest of existing update_ui code...
                elif item[0] == "DONE":
                    _, _, self.total_cards, _ = item
                    self.progress_bar["value"] = self.total_cards
                    self.progress_label.config(text=f"Progress: {self.total_cards}/{self.total_cards}")
                    self.processed_cards.clear()
                elif item[0] in ["TRANSLATE", "TTS", "Processing"]:
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
        api_keys = {
            'openai_key': self.openai_key_entry.get().strip(),
            'deepl_key': self.deepl_key_entry.get().strip()
        }
        os.makedirs(self.get_user_data_dir(), exist_ok=True)
        with open(self.get_api_keys_path(), 'w') as f:
            json.dump(api_keys, f)

    def load_api_keys(self):
        api_keys_path = self.get_api_keys_path()
        if os.path.exists(api_keys_path):
            with open(api_keys_path, 'r') as f:
                api_keys = json.load(f)
            self.openai_key = api_keys.get('openai_key', '')
            self.deepl_key = api_keys.get('deepl_key', '')

            # Populate the entry fields
            self.openai_key_entry.delete(0, tk.END)
            self.openai_key_entry.insert(0, self.openai_key)
            self.deepl_key_entry.delete(0, tk.END)
            self.deepl_key_entry.insert(0, self.deepl_key)