#!/usr/bin/env python3

import argparse
import platform
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


# ---------- Parsing Kindle Clippings ----------
def parse_clippings(file_path):
    with open(file_path, "r", encoding="utf-8-sig") as f:
        content = f.read()

    entries = content.split("==========")
    notes = []
    for entry in entries:
        lines = [line.strip() for line in entry.strip().split("\n") if line.strip()]
        if len(lines) >= 3:
            book = lines[0]
            text = lines[-1]
            notes.append({"book": book, "text": text})
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
def main(clippings, books, output):
    notes = parse_clippings(clippings)

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
