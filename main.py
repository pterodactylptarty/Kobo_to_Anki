import logging
import os
import appdirs
from kobo_anki_creator import KoboAnkiCreator


def setup_logging():
    log_dir = os.path.join(appdirs.user_data_dir("KoboAnkiCreator", "YourName_HobbyProjects"), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "kobo_anki_creator.log")

    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=log_file,
        filemode='w'
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info(f"Logging to file: {log_file}")


if __name__ == "__main__":
    setup_logging()
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


