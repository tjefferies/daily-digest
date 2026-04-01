"""Tests for the Embedder protocol and cosine similarity utility."""

import pytest

from digest.ingestion.embeddings import cosine_similarity


class TestCosineSimilarity:
    """Verify cosine similarity computation for continuation matching."""

    def test_identical_vectors_return_one(self) -> None:
        """Identical vectors have similarity 1.0."""
        assert cosine_similarity([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors_return_zero(self) -> None:
        """Orthogonal vectors have similarity 0.0."""
        assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors_return_negative_one(self) -> None:
        """Opposite vectors have similarity -1.0."""
        assert cosine_similarity([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self) -> None:
        """Zero vector produces 0.0 without division error."""
        assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)

    def test_both_zero_vectors_return_zero(self) -> None:
        """Two zero vectors produce 0.0."""
        assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == pytest.approx(0.0)

    def test_similar_vectors_high_similarity(self) -> None:
        """Near-identical vectors have similarity close to 1.0."""
        sim = cosine_similarity([1.0, 1.0, 0.0], [1.0, 0.9, 0.1])
        assert sim > 0.95

    def test_dissimilar_vectors_low_similarity(self) -> None:
        """Dissimilar vectors have low similarity."""
        sim = cosine_similarity([1.0, 0.0, 0.0], [0.0, 0.0, 1.0])
        assert sim == pytest.approx(0.0)

    def test_magnitude_invariant(self) -> None:
        """Cosine similarity is independent of vector magnitude."""
        sim_unit = cosine_similarity([1.0, 0.0], [0.707, 0.707])
        sim_scaled = cosine_similarity([100.0, 0.0], [70.7, 70.7])
        assert sim_unit == pytest.approx(sim_scaled, abs=0.01)
