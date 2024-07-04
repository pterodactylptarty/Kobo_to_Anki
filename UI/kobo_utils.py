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



class KoboUtils:
    def get_kobo_mountpoint(self, label: str = 'KOBOeReader') -> Optional[Path]:
        has_lsblk = shutil.which('lsblk')
        if has_lsblk:  # on Linux
            xxx = subprocess.check_output(['lsblk', '-f', '--json']).decode('utf8')
            jj = json.loads(xxx)
            devices = [d for d in jj['blockdevices'] if d.get('label', None) == label]
            kobos = []
            for d in devices:
                mp = d.get('mountpoint')
                if mp is not None:
                    kobos.append(mp)
                mps = d.get('mountpoints')
                if mps is not None:
                    assert all(p is not None for p in mps), (mps, d)
                    kobos.extend(mps)
        else:
            output = subprocess.check_output(('df', '-Hl')).decode('utf8')
            output_parts = [o.split() for o in output.split('\n')]
            kobos = [o[-1] for o in output_parts if f'/Volumes/{label}' in o]

        if len(kobos) > 1:
            raise RuntimeError(f'Multiple Kobo devices detected: {kobos}')
        elif len(kobos) == 0:
            return None
        else:
            [kobo] = kobos
            return Path(kobo)

    def fetch_books_and_authors(self, sort_by='Author', ownpath=None):
        if ownpath is None:
            kobo_path = self.get_kobo_mountpoint()
            if kobo_path is None:
                messagebox.showerror("Error", "No Kobo device detected")
                return
            conn = sqlite3.connect(kobo_path / '.kobo' / 'KoboReader.sqlite')
        else:
            conn = sqlite3.connect(ownpath)
        cursor = conn.cursor()

        if sort_by == 'Author':
            sort_column = 'Content.Attribution'
        elif sort_by == 'Book':
            sort_column = 'Content.Title'
        elif sort_by == 'Date Added':
            sort_column = 'Content.___SyncTime'

        query = f"""
        SELECT DISTINCT
            Content.Title AS Book,
            Content.Attribution AS Author,
            Content.___SyncTime 
        FROM 
            Content 
        WHERE
            Content.DateLastRead IS NOT NULL AND
            Content.Title IS NOT NULL AND
            Content.Attribution IS NOT NULL
        ORDER BY 
            {sort_column} ASC
        """

        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        self.listbox.delete(0, tk.END)

        header = f"{'Author':<30} | {'Book':<40} | {'Date Added':<20}"
        self.listbox.insert(tk.END, header)
        self.listbox.insert(tk.END, "-" * len(header))

        for result in results:
            author = result[1][:28] + '..' if len(result[1]) > 30 else result[1]
            book = result[0][:38] + '..' if len(result[0]) > 40 else result[0]
            date_added = result[2][:19]

            formatted_line = f"{author:<30} | {book:<40} | {date_added:<20}"
            self.listbox.insert(tk.END, formatted_line)

        self.listbox.config(font=("Courier", 16))

    def fetch_books_and_authors_with_sort(self):
        sort_by = self.sort_option.get()
        self.fetch_books_and_authors(sort_by)

    def fetch_annotations(self, author=None, title=None, start_date=None, end_date=None, ownpath=None):
        if ownpath is None:
            conn = sqlite3.connect(self.get_kobo_mountpoint() / '.kobo' / 'KoboReader.sqlite')
        else:
            conn = sqlite3.connect(ownpath)
        cursor = conn.cursor()

        query = """
        SELECT 
            Bookmark.Text,
            Bookmark.Annotation,
            Bookmark.DateCreated,
            AuthorContent.Attribution AS Author,
            ChapterContent.BookTitle
        FROM 
            Bookmark
        INNER JOIN 
            Content AS ChapterContent ON Bookmark.ContentID = ChapterContent.ContentID
        LEFT JOIN 
            Content AS AuthorContent ON ChapterContent.BookID = AuthorContent.ContentID AND AuthorContent.BookID IS NULL
        WHERE
            1=1
        """

        params = []

        if author:
            query += " AND AuthorContent.Attribution = ?"
            params.append(author)

        if title:
            query += " AND ChapterContent.BookTitle = ?"
            params.append(title)

        if start_date and end_date:
            query += " AND Bookmark.DateCreated BETWEEN ? AND ?"
            params.append(start_date)
            params.append(end_date)

        query += " ORDER BY Bookmark.DateCreated ASC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return results



    def fetch_and_translate(self, author=None, title=None, start_date=None, end_date=None, ownpath=None):
        if ownpath is None:
            conn = sqlite3.connect(self.get_kobo_mountpoint() / '.kobo' / 'KoboReader.sqlite')
        else:
            conn = sqlite3.connect(ownpath)
        cursor = conn.cursor()

        query = """
        SELECT 
            Bookmark.Text,
            Bookmark.Annotation,
            Bookmark.DateCreated,
            AuthorContent.Attribution AS Author,
            ChapterContent.BookTitle
        FROM 
            Bookmark
        INNER JOIN 
            Content AS ChapterContent ON Bookmark.ContentID = ChapterContent.ContentID
        LEFT JOIN 
            Content AS AuthorContent ON ChapterContent.BookID = AuthorContent.ContentID AND AuthorContent.BookID IS NULL
        WHERE
            1=1
        """

        params = []

        if author:
            query += " AND AuthorContent.Attribution = ?"
            params.append(author)

        if title:
            query += " AND ChapterContent.BookTitle = ?"
            params.append(title)

        if start_date and end_date:
            query += " AND Bookmark.DateCreated BETWEEN ? AND ?"
            params.append(start_date)
            params.append(end_date)

        query += " ORDER BY Bookmark.DateCreated ASC"

        cursor.execute(query, params)
        results = cursor.fetchall()
        cursor.close()

        modified_rows = []
        for index, result in enumerate(results, 1):
            original_text = result[0]
            translation = self.translator.translate_text(original_text, target_lang="EN-US").text

            modified_row = result[:1] + (translation,) + result[1:]
            modified_rows.append(modified_row)

            yield index, len(results), original_text, translation

        return modified_rows

