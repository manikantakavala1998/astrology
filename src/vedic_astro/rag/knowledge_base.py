"""Local, persistent vector store (ChromaDB) for the RAG knowledge base.

Embeddings are computed elsewhere (embeddings.py, via Ollama) and passed in
directly here - Chroma's own built-in embedding functions are not used, so
embedding generation stays in one place. Storage is a local directory
(SQLite-backed) - no server process, no network calls.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import chromadb

DEFAULT_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "knowledge_base_store"
_COLLECTION_NAME = "astrology_knowledge"


def _get_collection(store_path: Path) -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(store_path))
    return client.get_or_create_collection(name=_COLLECTION_NAME)


def add_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    source: str,
    store_path: Path = DEFAULT_STORE_PATH,
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must be the same length")
    if not chunks:
        return
    collection = _get_collection(store_path)
    ids = [f"{source}:{i}" for i in range(len(chunks))]
    collection.upsert(
        ids=ids,
        embeddings=cast(Any, embeddings),
        documents=chunks,
        metadatas=[{"source": source} for _ in chunks],
    )


def query(embedding: list[float], top_k: int = 5, store_path: Path = DEFAULT_STORE_PATH) -> list[str]:
    collection = _get_collection(store_path)
    count = collection.count()
    if count == 0:
        return []
    results = collection.query(query_embeddings=cast(Any, [embedding]), n_results=min(top_k, count))
    documents = results.get("documents")
    if not documents:
        return []
    return list(documents[0])


def reset(store_path: Path = DEFAULT_STORE_PATH) -> None:
    """Delete all entries - used when re-ingesting a knowledge base from scratch."""
    client = chromadb.PersistentClient(path=str(store_path))
    existing_names = {c.name for c in client.list_collections()}
    if _COLLECTION_NAME in existing_names:
        client.delete_collection(_COLLECTION_NAME)


def count(store_path: Path = DEFAULT_STORE_PATH) -> int:
    return _get_collection(store_path).count()
