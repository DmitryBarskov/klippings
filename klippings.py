#!/usr/bin/env python3

import argparse
import platform
import re
from pathlib import Path
from ebooklib import epub
from bs4 import BeautifulSoup
from pypdf import PdfReader


def default_clippings_path():
    os = platform.system()
    if os == "Darwin":
        return "/Volumes/Kindle/documents/My Clippings.txt"
    else:
        return None


def parse_meta(meta_line: str):
    """
    >>> parse_meta('- Your Bookmark on Location 2473 | Added on Tuesday, September 2, 2025 12:08:11 AM')
    {'type': 'Bookmark', 'page': None, 'location': '2473'}
    >>> parse_meta('- Your Highlight on page 379 | Location 2805-2806 | Added on Sunday, August 31, 2025 12:10:21 AM')
    {'type': 'Highlight', 'page': '379', 'location': '2805-2806'}
    >>> parse_meta('- Your Bookmark on page 343-344 | Added on Sunday, February 16, 2025 10:08:13 PM')
    {'type': 'Bookmark', 'page': '343-344', 'location': None}
    """

    match_obj = re.match(r'- Your (?P<type>Bookmark|Highlight) on (page (?P<pg_only>\d+(-\d+)?)|Location (?P<loc_only>\d+(-\d+)?)|page (?P<pg>\d+) \| Location (?P<loc>\d+(-\d+)?)) \| Added.*', meta_line)
    groups = match_obj.groupdict() if match_obj is not None else {}
    return {
        'type': groups.get('type'),
        'page': groups.get('pg_only') or groups.get('pg'),
        'location': groups.get('loc_only') or groups.get('loc'),
    }


# ---------- Parsing Kindle Clippings ----------
def parse_clippings(content: str):
    """
    >>> s = '''
    ... Steven Low, DPT - Overcoming Gravity
    ... - Your Highlight on Location 2572-2573 | Added on Tuesday, July 2, 2024 12:08:10 AM
    ...
    ... inverted hang and then back again
    ... ==========
    ... Steven Low, DPT - Overcoming Gravity
    ... - Your Highlight on Location 3042-3043 | Added on Friday, July 12, 2024 1:45:31 AM
    ...
    ... Planche isometrics fall solidly into the
    ... ==========
    ... Steven Low - Overcoming Gravity Advanced Programming
    ... - Your Highlight on page 11 | Location 170-172 | Added on Sunday, February 9, 2025 12:26:53 PM
    ...
    ... Since your goal is primarily strength increases
    ... ==========
    ... Адитья Бхаргава - Грокаем алгоритмы
    ... - Your Bookmark on page 343 | Added on Sunday, February 16, 2025 10:08:13 PM
    ... '''
    >>> list(parse_clippings(s))
    [{'book': 'Steven Low, DPT - Overcoming Gravity', 'text': 'inverted hang and then back again', 'type': 'Highlight', 'page': None, 'location': '2572-2573'}, {'book': 'Steven Low, DPT - Overcoming Gravity', 'text': 'Planche isometrics fall solidly into the', 'type': 'Highlight', 'page': None, 'location': '3042-3043'}, {'book': 'Steven Low - Overcoming Gravity Advanced Programming', 'text': 'Since your goal is primarily strength increases', 'type': 'Highlight', 'page': '11', 'location': '170-172'}]
    """

    entries = content.split("==========")
    notes_by_book = {}
    for entry in entries:
        lines = [line.strip() for line in entry.strip().split("\n") if line.strip()]
        if len(lines) >= 3:
            book, meta, *text = lines

            if book not in notes_by_book:
                notes_by_book[book] = []
            notes_by_book[book].append({"book": book, "text": "\n".join(text), **parse_meta(meta)})
    notes = []
    for single_book_notes in notes_by_book.values():
        for note in single_book_notes:
            notes.append(note)
    return notes


# ---------- EPUB Search ----------
def search_epub(book_path, note, context=200):
    try:
        book = epub.read_epub(book_path)
        for item in book.get_items():
            if item.get_type() == 9:  # DOCUMENT
                soup = BeautifulSoup(item.get_body_content(), "html.parser")
                text = soup.get_text(" ")
                idx = text.find(note)
                if idx != -1:
                    start = max(0, idx - context)
                    end = min(len(text), idx + len(note) + context)
                    return text[start:end]
        return None
    except KeyError:
        print(f"Failed to read {book_path}!")


# ---------- PDF Search ----------
def search_pdf(book_path, note, context=200):
    reader = PdfReader(book_path)
    for page in reader.pages:
        text = page.extract_text()
        if not text:
            continue
        idx = text.find(note)
        if idx != -1:
            start = max(0, idx - context)
            end = min(len(text), idx + len(note) + context)
            return text[start:end]
    return None


# ---------- Match Clippings to Books ----------
def find_context(note, books_folder):
    for ext in ("*.epub", "*.pdf"):
        for path in Path(books_folder).rglob(ext):
            if note["book"].split("(")[0].strip().lower() in path.stem.lower():
                if path.suffix == ".epub":
                    return search_epub(path, note["text"])
                elif path.suffix == ".pdf":
                    return search_pdf(path, note["text"])
    return None


# ---------- Main ----------
def main(clippings_path: str, books, output):
    with open(clippings_path, "r", encoding="utf-8") as f:
        content = f.read()
        notes = parse_clippings(content)

        with open(output, "w", encoding="utf-8") as out:
            for note in notes:
                context = find_context(note, books)
                out.write(f"## {note['book']}\n\n")
                out.write(f"**Note:** {note['text']}\n\n")
                if context:
                    out.write(f"**Context:** {context}\n\n")
                else:
                    out.write("**Context:** Not found\n\n")
                out.write("---\n\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    default_clippings = default_clippings_path()
    if default_clippings_path is None:
        parser.add_argument("--clippings", required=True, help="Path to My Clippings.txt")
    else:
        parser.add_argument("--clippings", required=False, help="Path to My Clippings.txt", default=default_clippings)
    parser.add_argument("--books", required=True, help="Path to folder with epub/pdf")
    parser.add_argument("--output", default="notes.md", help="Output file")
    args = parser.parse_args()

    main(args.clippings, args.books, args.output)
