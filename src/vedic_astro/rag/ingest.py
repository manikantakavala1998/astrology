"""Document parsing + chunking for the knowledge base.

Supports PDF, DOCX, TXT/MD, CSV, and XLSX source files - whatever format the
user's astrology reference material happens to be in. Parsing is entirely
local (no network calls); each format's library reads the file directly off
disk.
"""

from __future__ import annotations

import csv
from pathlib import Path

import openpyxl
import pypdf
from docx import Document

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx"}


def _extract_pdf(path: Path) -> str:
    reader = pypdf.PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages)


def _extract_docx(path: Path) -> str:
    document = Document(str(path))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _extract_csv(path: Path) -> str:
    lines: list[str] = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            cells = [cell.strip() for cell in row if cell.strip()]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


def _extract_xlsx(path: Path) -> str:
    workbook = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    lines: list[str] = []
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            cells = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
            if cells:
                lines.append(" | ".join(cells))
    return "\n".join(lines)


_EXTRACTORS = {
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
    ".txt": _extract_text_file,
    ".md": _extract_text_file,
    ".csv": _extract_csv,
    ".xlsx": _extract_xlsx,
}


def extract_text(path: Path) -> str:
    extension = path.suffix.lower()
    extractor = _EXTRACTORS.get(extension)
    if extractor is None:
        raise ValueError(
            f"Unsupported file type {extension!r} for {path.name}; "
            f"supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return extractor(path)


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    """Paragraph-aware chunking: greedily packs paragraphs up to chunk_size,
    splitting an individual over-long paragraph by character windows.
    Consecutive chunks share `overlap` characters of trailing context.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    raw_chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                raw_chunks.append(current)
                current = ""
            start = 0
            while start < len(paragraph):
                raw_chunks.append(paragraph[start : start + chunk_size])
                start += chunk_size - overlap
            continue

        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                raw_chunks.append(current)
            current = paragraph
    if current:
        raw_chunks.append(current)

    chunks: list[str] = []
    for i, chunk in enumerate(raw_chunks):
        if i > 0 and overlap > 0:
            tail = raw_chunks[i - 1][-overlap:]
            chunk = f"{tail} {chunk}"
        chunks.append(chunk.strip())
    return chunks


def ingest_file(path: Path, chunk_size: int = 700, overlap: int = 100) -> list[str]:
    text = extract_text(path)
    return chunk_text(text, chunk_size=chunk_size, overlap=overlap)
