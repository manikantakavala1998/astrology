"""CLI: (re)build the RAG knowledge base vector store from source documents.

Usage:
    python scripts/ingest_knowledge_base.py [source_dir]

Defaults to src/vedic_astro/data/knowledge_base_source/ (a small sample set
of notes). Point it at a different folder - containing your own PDF, DOCX,
TXT/MD, CSV, or XLSX files - to build the knowledge base from your own
material instead. Re-run any time you add or change source files; this
clears and fully rebuilds the store each run.

Fully offline except for local calls to Ollama (127.0.0.1) for embeddings.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from vedic_astro.rag import knowledge_base  # noqa: E402
from vedic_astro.rag.embeddings import embed_many  # noqa: E402
from vedic_astro.rag.ingest import SUPPORTED_EXTENSIONS, ingest_file  # noqa: E402

DEFAULT_SOURCE_DIR = (
    Path(__file__).resolve().parent.parent / "src" / "vedic_astro" / "data" / "knowledge_base_source"
)


def main(source_dir: Path, store_path: Path = knowledge_base.DEFAULT_STORE_PATH) -> int:
    if not source_dir.exists():
        raise SystemExit(f"Source directory not found: {source_dir}")

    files = sorted(
        path for path in source_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not files:
        raise SystemExit(f"No supported documents ({sorted(SUPPORTED_EXTENSIONS)}) found in {source_dir}")

    print(f"Rebuilding knowledge base from {len(files)} file(s) in {source_dir}")
    knowledge_base.reset(store_path=store_path)

    total_chunks = 0
    for path in files:
        chunks = ingest_file(path)
        if not chunks:
            print(f"  {path.name}: no text extracted, skipping")
            continue
        print(f"  {path.name}: {len(chunks)} chunk(s), embedding...")
        embeddings = embed_many(chunks)
        knowledge_base.add_chunks(chunks, embeddings, source=path.name, store_path=store_path)
        total_chunks += len(chunks)

    print(f"Done. {total_chunks} chunk(s) indexed. Store: {store_path}")
    return total_chunks


if __name__ == "__main__":
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE_DIR
    main(source)
