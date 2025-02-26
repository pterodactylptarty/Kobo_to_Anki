# Kobo to Anki Card Generator

![Screenshot 2025-02-26 at 10 28 57 AM](https://github.com/user-attachments/assets/f8c83e7b-c7f0-438c-8013-c4c431907773)


This project extracts annotations from a Kobo eReader and converts them into Anki flashcards with text and audio for language learning. You can also instead upload a text file, with each word/phrase to be translated on its own line. It should translate from any language into English, with the target language on the front and English on the back. It uses DeepL API (free) for translation and has the option to use the OpenAI API for text to speech generation. The newly created decks can either be manually added to Anki or automatically uploaded using AnkiConnect.

The program should automatically connect to the Kobo if it is plugged in to the computer, however there is also the option to manually direct to the SQLite database if the automatic connection isn't working.

You can download the app for mac here: https://github.com/pterodactylptarty/Kobo_to_Anki/releases/tag/v1.0.0
I will upload one for windows soon, but in the meantime you can just download the python scripts and run main.py in an IDE.


## License

This project is licensed under the MIT License.


