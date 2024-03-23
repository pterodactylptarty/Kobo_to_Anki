from .functions import create_deck, print_first_rows, make_anki_cards, bundle_anki_package, delete_media_files
import argparse

media_list = []



def main():
    parser = argparse.ArgumentParser(description="Extract annotations from a Kobo device.")
    parser.add_argument('--deck-name', help='Name of Anki Deck to create.', required=True)
    parser.add_argument('--author', help='Filter annotations by author name.')
    parser.add_argument('--title', help='Filter annotations by book title.')
    parser.add_argument('--start-date', help='Start date for filtering annotations (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date for filtering annotations (YYYY-MM-DD).')
    parser.add_argument('--own-path', help='Enter own path to file if not connecting directly to kobo.')
    parser.add_argument('--file-name', help='Name of the output anki package')
    args = parser.parse_args()

    # Set the default file name based on the deck name if not specified
    if not args.file_name:
        args.file_name = f"{args.deck_name}.apkg"


    ## 1. Create new deck with its own name
    deck = create_deck(args.deck_name)


    # 1.1 Show first few rows to confirm
    # Wait for user confirmation
#def print_first_rows(author=None, title=None, start_date=None, end_date=None, ownpath=None, translate=False):

    print_first_rows(args.author, args.title, args.start_date, args.end_date, args.own_path, translate=True)   ### Todo: change so users can also export untranslated
    input("Press Enter to continue or Ctrl+C to abort...")


    ##2. package anki cards into deck and deck make media.
    make_anki_cards(deck, media_list, args.author, args.title, args.start_date, args.end_date, args.own_path)

    #3. Package media and deck together into anki package
    bundle_anki_package(deck, media_list, args.file_name)

    #4. delete audio files to reduce clutter
    delete_media_files(media_list)


if __name__ == "__main__":
    main()



## todo: add option for users to export as csv,
