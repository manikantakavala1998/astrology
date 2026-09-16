import csv
from pathlib import Path

import openpyxl
import pytest
from docx import Document

from vedic_astro.rag.ingest import chunk_text, extract_text, ingest_file


def test_chunk_text_combines_short_paragraphs() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, chunk_size=1000, overlap=0)
    assert len(chunks) == 1
    assert "First paragraph." in chunks[0]
    assert "Third paragraph." in chunks[0]


def test_chunk_text_splits_when_exceeding_chunk_size() -> None:
    paragraph_a = "A" * 400
    paragraph_b = "B" * 400
    text = f"{paragraph_a}\n\n{paragraph_b}"
    chunks = chunk_text(text, chunk_size=500, overlap=0)
    assert len(chunks) == 2
    assert paragraph_a in chunks[0]
    assert paragraph_b in chunks[1]


def test_chunk_text_splits_an_over_long_single_paragraph() -> None:
    huge_paragraph = "X" * 2000
    chunks = chunk_text(huge_paragraph, chunk_size=700, overlap=100)
    assert len(chunks) > 1
    # +1 for the joining space between the overlap tail and the chunk itself.
    assert all(len(c) <= 700 + 100 + 1 for c in chunks)


def test_chunk_text_adds_overlap_between_consecutive_chunks() -> None:
    paragraph_a = "A" * 400
    paragraph_b = "B" * 400
    text = f"{paragraph_a}\n\n{paragraph_b}"
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    # The second chunk should start with a tail of the first chunk's content.
    assert chunks[1].startswith("A" * 50)


def test_chunk_text_empty_input_returns_nothing() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n\n  ") == []


def test_extract_text_unsupported_extension_raises(tmp_path: Path) -> None:
    bad_file = tmp_path / "notes.xyz"
    bad_file.write_text("hello")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(bad_file)


def test_extract_text_from_txt(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("Mars in the 7th house indicates a strong-willed partner.", encoding="utf-8")
    assert "strong-willed partner" in extract_text(path)


def test_extract_text_from_docx(tmp_path: Path) -> None:
    path = tmp_path / "sample.docx"
    document = Document()
    document.add_paragraph("Venus Mahadasha commonly brings relationships and comfort.")
    document.add_paragraph("Saturn Mahadasha often brings discipline and delay.")
    document.save(str(path))

    text = extract_text(path)
    assert "Venus Mahadasha" in text
    assert "Saturn Mahadasha" in text


def test_extract_text_from_csv(tmp_path: Path) -> None:
    path = tmp_path / "sample.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Topic", "Meaning"])
        writer.writerow(["Nadi Dosha", "Same nadi indicates health/genetic incompatibility"])

    text = extract_text(path)
    assert "Nadi Dosha" in text
    assert "Same nadi indicates health/genetic incompatibility" in text


def test_extract_text_from_xlsx(tmp_path: Path) -> None:
    path = tmp_path / "sample.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["Topic", "Meaning"])
    sheet.append(["Bhakoot Dosha", "Rashi distance of 6-8 or 2-12 causes this dosha"])
    workbook.save(str(path))

    text = extract_text(path)
    assert "Bhakoot Dosha" in text
    assert "Rashi distance" in text


def test_ingest_file_returns_chunks(tmp_path: Path) -> None:
    path = tmp_path / "sample.txt"
    path.write_text("Paragraph one.\n\nParagraph two.\n\nParagraph three.", encoding="utf-8")
    chunks = ingest_file(path, chunk_size=1000, overlap=0)
    assert len(chunks) == 1
    assert "Paragraph one." in chunks[0]
