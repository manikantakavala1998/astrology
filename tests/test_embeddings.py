import math

from vedic_astro.rag.embeddings import embed, embed_many


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b)


def test_embed_returns_a_nonempty_vector() -> None:
    vector = embed("Mars in the 7th house indicates a strong-willed partner.")
    assert len(vector) > 0
    assert all(isinstance(x, float) for x in vector)


def test_embed_is_deterministic_for_the_same_text() -> None:
    vector_a = embed("Venus Mahadasha brings relationships.")
    vector_b = embed("Venus Mahadasha brings relationships.")
    assert vector_a == vector_b


def test_embed_similar_texts_are_closer_than_unrelated_ones() -> None:
    mars_1 = embed("Mars in the 7th house indicates conflict in marriage.")
    mars_2 = embed("Mars placed in the 7th house can cause marital disputes.")
    unrelated = embed("The stock market closed higher today on strong earnings.")

    similar_score = _cosine_similarity(mars_1, mars_2)
    unrelated_score = _cosine_similarity(mars_1, unrelated)
    assert similar_score > unrelated_score


def test_embed_many_matches_individual_embed_dimensionality() -> None:
    vectors = embed_many(["first text", "second text"])
    assert len(vectors) == 2
    assert len(vectors[0]) == len(embed("first text"))


def test_embed_many_empty_list_returns_empty() -> None:
    assert embed_many([]) == []
