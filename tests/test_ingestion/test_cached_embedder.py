"""Tests for CachedEmbedder: FAISS-backed embedding deduplication."""

from __future__ import annotations

from typing import TYPE_CHECKING

from evercurrent.ingestion.vectorstore import VectorStore

if TYPE_CHECKING:
    from evercurrent.ingestion.embeddings import Embedder


class CountingEmbedder:
    """Test embedder that counts how many texts it embeds.

    Args:
        dim: Dimensionality of output vectors.
    """

    def __init__(self, dim: int = 3) -> None:
        """Initialize with a fixed dimensionality.

        Args:
            dim: Dimensionality of output vectors.
        """
        self._dim = dim
        self.call_count = 0
        self.texts_embedded: list[str] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return simple vectors and track what was embedded.

        Args:
            texts: List of texts to embed.

        Returns:
            List of vectors with incrementing first component.
        """
        self.call_count += 1
        self.texts_embedded.extend(texts)
        return [[float(i + 1)] + [0.0] * (self._dim - 1) for i in range(len(texts))]


_: type[Embedder] = CountingEmbedder  # type: ignore[assignment]


class TestCachedEmbedder:
    """Tests for the CachedEmbedder wrapper."""

    def test_cache_miss_delegates_to_inner(self) -> None:
        """Uncached texts are passed to the inner embedder."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        store = VectorStore(dim=3)
        inner = CountingEmbedder(dim=3)
        cached = CachedEmbedder(inner, store)

        result = cached.embed(["hello", "world"])

        assert len(result) == 2
        assert inner.call_count == 1
        assert inner.texts_embedded == ["hello", "world"]

    def test_cache_hit_skips_inner(self) -> None:
        """Cached texts are returned from store without calling inner."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        store = VectorStore(dim=3)
        store.add("hello", [1.0, 0.0, 0.0])
        store.add("world", [0.0, 1.0, 0.0])
        inner = CountingEmbedder(dim=3)
        cached = CachedEmbedder(inner, store)

        result = cached.embed(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [1.0, 0.0, 0.0]
        assert result[1] == [0.0, 1.0, 0.0]
        assert inner.call_count == 0

    def test_mixed_hit_and_miss(self) -> None:
        """Only uncached texts are sent to the inner embedder."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        store = VectorStore(dim=3)
        store.add("cached", [9.0, 0.0, 0.0])
        inner = CountingEmbedder(dim=3)
        cached = CachedEmbedder(inner, store)

        result = cached.embed(["cached", "new_text"])

        assert len(result) == 2
        assert result[0] == [9.0, 0.0, 0.0]  # from store
        assert inner.call_count == 1
        assert inner.texts_embedded == ["new_text"]

    def test_new_embeddings_stored_in_cache(self) -> None:
        """After embedding, new vectors are stored in the VectorStore."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        store = VectorStore(dim=3)
        inner = CountingEmbedder(dim=3)
        cached = CachedEmbedder(inner, store)

        cached.embed(["text_a"])

        assert "text_a" in store
        assert store.get("text_a") is not None

    def test_second_call_uses_cache(self) -> None:
        """Embedding the same text twice only calls inner once."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        store = VectorStore(dim=3)
        inner = CountingEmbedder(dim=3)
        cached = CachedEmbedder(inner, store)

        cached.embed(["hello"])
        cached.embed(["hello"])

        assert inner.call_count == 1

    def test_stats_track_hits_and_misses(self) -> None:
        """CachedEmbedder tracks cache hit/miss counts."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        store = VectorStore(dim=3)
        store.add("cached", [1.0, 0.0, 0.0])
        inner = CountingEmbedder(dim=3)
        cached = CachedEmbedder(inner, store)

        cached.embed(["cached", "new"])

        assert cached.stats["cache_hits"] == 1
        assert cached.stats["cache_misses"] == 1

    def test_empty_input(self) -> None:
        """Empty input returns empty output without calling inner."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        store = VectorStore(dim=3)
        inner = CountingEmbedder(dim=3)
        cached = CachedEmbedder(inner, store)

        result = cached.embed([])

        assert result == []
        assert inner.call_count == 0
