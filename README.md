# Kobo to Anki Card Generator

This project extracts annotations from a Kobo eReader and converts them into Anki flashcards with text and audio for language learning. It should translate from any language into English, with the target language on the front and English on the back. It uses DeepL for translation and OpenAI for text to speech generation. The newly created decks can either be manually added to Anki or automatically uploaded using AnkiConnect.

The program should automatically connect to the Kobo if it is plugged in to the computer, however there is also the option to manually direct to the SQLite database if the automatic connection isn't working.

July 1, 2024 Update: Added a way to use this with a UI because running it by command line was annoying. Now only the UI_script.py and api_keys.py script need to be downloaded, and the whole tool can be used by running the ui_script.py file. You just need to replace the deepL and openai api keys with your own.

Leaving the command line-based script up in the src directory in case it is useful for anyone, but the UI script is definitely is easier to use. 


## Features

- Extracts annotations from a Kobo eReader or a provided SQLite database.
- Filters annotations by author, title, and date range.
- Translates annotations using DeepL API.
- Generates text-to-speech files for annotations using OpenAI API.
- Creates Anki flashcards with the option to package and import them into Anki automatically.

## Requirements

- Python 3.7+
- AnkiConnect (for automatic importing into Anki)
- DeepL API key
- OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/pterodactylptarty/kobo-to-anki.git
   cd kobo-to-anki
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Make sure AnkiConnect is installed and running in Anki. You can get it from [here](https://ankiweb.net/shared/info/2055492159).

## Usage

The script can be run from the command line with various options to customize the extraction and conversion process.

```bash
python -m src --deck-name "My Deck" --author "Author Name" --title "Book Title" --start-date "2024-01-01" --end-date "2024-01-31" --own-path "/path/to/KoboReader.sqlite" --file-name "output.apkg" --list-books --import-to-anki --deepL-key "your-deepl-key" --openai-key "your-openai-key"
```

### Arguments

- `--deck-name`: Name of the Anki deck to create. Defaults to the current date if not provided.
- `--author`: Filter annotations by author name.
- `--title`: Filter annotations by book title.
- `--start-date`: Start date for filtering annotations (YYYY-MM-DD).
- `--end-date`: End date for filtering annotations (YYYY-MM-DD).
- `--own-path`: Path to the KoboReader SQLite database file if not connecting directly to the Kobo device.
- `--file-name`: Name of the output Anki package file.
- `--list-books`: List available books and authors from the database and exit. 
- `--import-to-anki`: Import the generated deck to Anki after creating it.
- `--deepL-key`: Your DeepL API key.
- `--openai-key`: Your OpenAI API key.

### Examples

#### List available books and authors
```bash
python -m src --list-books --own-path "/path/to/KoboReader.sqlite"
```

#### Create an Anki deck with annotations from a specific author and date range
```bash
python -m src --deck-name "My Deck" --author "Author Name" --start-date "2024-01-01" --end-date "2024-01-31" --deepL-key "your-deepl-key" --openai-key "your-openai-key"
```

#### Import the created deck into Anki
```bash
python -m src --deck-name "My Deck" --file-name "output.apkg" --import-to-anki --deepL-key "your-deepl-key" --openai-key "your-openai-key"
```


## Configuration

To configure AnkiConnect, ensure you have the correct URL for your setup. By default, the script uses `http://localhost:8765`. If your AnkiConnect is running on a different URL or port, modify the `import_deck_to_anki` function in `functions.py` accordingly.

## License

This project is licensed under the MIT License.
