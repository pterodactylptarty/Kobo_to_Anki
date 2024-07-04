import logging
from kobo_anki_creator import KoboAnkiCreator

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