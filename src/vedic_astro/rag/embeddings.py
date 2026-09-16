"""Text embeddings via Ollama's local /api/embed endpoint - no network calls,
Ollama runs entirely on 127.0.0.1.
"""

from __future__ import annotations

import httpx

OLLAMA_BASE_URL = "http://127.0.0.1:11434"
EMBEDDING_MODEL = "nomic-embed-text"


def embed(text: str, model: str = EMBEDDING_MODEL, base_url: str = OLLAMA_BASE_URL) -> list[float]:
    response = httpx.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": text},
        timeout=60.0,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Ollama embeddings error: {data['error']}")
    return list(data["embeddings"][0])


def embed_many(texts: list[str], model: str = EMBEDDING_MODEL, base_url: str = OLLAMA_BASE_URL) -> list[list[float]]:
    if not texts:
        return []
    response = httpx.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": texts},
        timeout=120.0,
    )
    response.raise_for_status()
    data = response.json()
    if "error" in data:
        raise RuntimeError(f"Ollama embeddings error: {data['error']}")
    return [list(vector) for vector in data["embeddings"]]
