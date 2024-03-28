from .functions import create_deck, print_first_rows, make_anki_cards, bundle_anki_package, delete_media_files, fetch_books_and_authors
from .constants import german, italian
import argparse

media_list = []



def main():
    parser = argparse.ArgumentParser(description="Extract annotations from a Kobo device.")
    parser.add_argument('--deck-name', help='Name of Anki Deck to create. (defaults to date)')
    parser.add_argument('--author', help='Filter annotations by author name.')
    parser.add_argument('--title', help='Filter annotations by book title.')
    parser.add_argument('--start-date', help='Start date for filtering annotations (YYYY-MM-DD).')
    parser.add_argument('--end-date', help='End date for filtering annotations (YYYY-MM-DD).')
    parser.add_argument('--own-path', help='Enter own path to file if not connecting directly to kobo.')
    parser.add_argument('--file-name', help='Name of the output anki package')
    parser.add_argument('--list-books', action='store_true', help='List available books and authors and exit.')
    args = parser.parse_args()

    if args.list_books:
        fetch_books_and_authors(args.own_path)
        exit()

    ## 1. Create new deck with its own name
    deck = create_deck(args.deck_name)


    # 1.1 Show first few rows to confirm
    # Wait for user confirmation
#def print_first_rows(author=None, title=None, start_date=None, end_date=None, ownpath=None, translate=False):

    print_first_rows(args.author, args.title, args.start_date, args.end_date, args.own_path, translate=True)
    input("Press Enter to continue or Ctrl+C to abort...")


    ##2. package anki cards into deck and deck make media.
    make_anki_cards(deck, media_list, args.author, args.title, args.start_date, args.end_date, args.own_path)

    #3. Package media and deck together into anki package
    bundle_anki_package(deck, media_list, args.file_name)


    #4. delete audio files to reduce clutter
    delete_media_files(media_list)


if __name__ == "__main__":
    main()



## todo: add option to export as csv, with audio put in a folder. Seems cumbursome but necessary for updating a deck.
    ## maybe first see if there is an option to search through and add to an exisiting deck
## todo: also need option for reading a csv file to skip highlights that have already been added.

## todo: add reverse note option for highlights with a note. (idea, annotate 'r' for reverse cards). Also maype specific tags for idioms.