"""Integration test: FAISS vectorstore persist and reload."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from evercurrent.ingestion.embeddings import cosine_similarity
from evercurrent.ingestion.vectorstore import VectorStore

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.integration
class TestFAISSRoundTrip:
    """Test FAISS vectorstore save/load with real vectors."""

    def test_persist_reload_preserves_vectors(self, tmp_path: Path) -> None:
        """Vectors survive a save/load cycle with correct cosine similarity."""
        store = VectorStore(dim=4)
        store.add("motor overheating", [0.9, 0.1, 0.0, 0.0])
        store.add("thermal paste issue", [0.85, 0.15, 0.0, 0.0])
        store.add("lunch plans", [0.0, 0.0, 0.0, 1.0])

        path = tmp_path / "test.index"
        store.save(path)

        loaded = VectorStore.load(path)
        assert len(loaded) == 3

        motor = loaded.get("motor overheating")
        thermal = loaded.get("thermal paste issue")
        lunch = loaded.get("lunch plans")

        assert motor is not None
        assert thermal is not None
        assert lunch is not None

        # Related vectors should be similar
        sim = cosine_similarity(motor, thermal)
        assert sim > 0.8

        # Unrelated vectors should be dissimilar
        sim_unrelated = cosine_similarity(motor, lunch)
        assert sim_unrelated < 0.3

    def test_cached_embedder_roundtrip(self, tmp_path: Path) -> None:
        """CachedEmbedder stores new embeddings that survive reload."""
        from evercurrent.ingestion.cached_embedder import CachedEmbedder

        class SimpleEmbedder:
            """Test embedder returning incrementing vectors."""

            def embed(self, texts: list[str]) -> list[list[float]]:
                """Return simple vectors."""
                return [[float(i + 1), 0.0, 0.0] for i in range(len(texts))]

        store = VectorStore(dim=3)
        cached = CachedEmbedder(SimpleEmbedder(), store)

        # First call embeds
        cached.embed(["hello", "world"])
        assert cached.stats["cache_misses"] == 2

        # Save and reload
        path = tmp_path / "cache.index"
        store.save(path)
        store2 = VectorStore.load(path)
        cached2 = CachedEmbedder(SimpleEmbedder(), store2)

        # Second call should hit cache
        cached2.embed(["hello", "world"])
        assert cached2.stats["cache_hits"] == 2
        assert cached2.stats["cache_misses"] == 0
