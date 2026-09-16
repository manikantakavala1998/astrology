from pathlib import Path

import pytest

from vedic_astro.rag import knowledge_base as kb


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "kb_store"


def test_add_and_query_returns_nearest_chunk(store_path: Path) -> None:
    chunks = ["Mars in the 7th house text", "Venus dasha text", "Nadi Dosha text"]
    embeddings = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    kb.add_chunks(chunks, embeddings, source="sample.txt", store_path=store_path)

    results = kb.query([0.9, 0.1, 0.0], top_k=1, store_path=store_path)
    assert results == ["Mars in the 7th house text"]


def test_query_returns_top_k_ordered_by_similarity(store_path: Path) -> None:
    chunks = ["A", "B", "C"]
    embeddings = [[1.0, 0.0], [0.9, 0.1], [0.0, 1.0]]
    kb.add_chunks(chunks, embeddings, source="sample.txt", store_path=store_path)

    results = kb.query([1.0, 0.0], top_k=2, store_path=store_path)
    assert results == ["A", "B"]


def test_query_on_empty_store_returns_nothing(store_path: Path) -> None:
    assert kb.query([1.0, 0.0], store_path=store_path) == []


def test_add_chunks_mismatched_lengths_raises(store_path: Path) -> None:
    with pytest.raises(ValueError, match="same length"):
        kb.add_chunks(["a", "b"], [[1.0, 0.0]], source="x", store_path=store_path)


def test_add_chunks_empty_list_is_a_noop(store_path: Path) -> None:
    kb.add_chunks([], [], source="x", store_path=store_path)
    assert kb.count(store_path=store_path) == 0


def test_reset_clears_the_collection(store_path: Path) -> None:
    kb.add_chunks(["A"], [[1.0, 0.0]], source="x", store_path=store_path)
    assert kb.count(store_path=store_path) == 1
    kb.reset(store_path=store_path)
    assert kb.count(store_path=store_path) == 0


def test_reset_on_empty_store_does_not_error(store_path: Path) -> None:
    kb.reset(store_path=store_path)  # should not raise even if nothing exists yet
    assert kb.count(store_path=store_path) == 0


def test_add_chunks_upserts_same_source_without_duplicating(store_path: Path) -> None:
    kb.add_chunks(["A", "B"], [[1.0, 0.0], [0.0, 1.0]], source="doc", store_path=store_path)
    kb.add_chunks(["A2", "B2"], [[1.0, 0.0], [0.0, 1.0]], source="doc", store_path=store_path)
    assert kb.count(store_path=store_path) == 2
