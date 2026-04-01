"""FAISS-cached embedder: skips recomputation for already-stored texts.

Wraps an inner Embedder and a VectorStore. On each embed() call,
checks the store for cached vectors, only delegates uncached texts
to the inner embedder, then stores the new vectors. Tracks cache
hit/miss statistics.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from digest.ingestion.embeddings import Embedder
    from digest.ingestion.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class CachedEmbedder:
    """Embedding wrapper that caches results in a VectorStore.

    Checks the FAISS-backed store before calling the inner embedder.
    Only computes embeddings for texts not already cached. New
    embeddings are stored after computation.

    Attributes:
        stats: Dict tracking cache_hits and cache_misses.
    """

    def __init__(self, inner: Embedder, store: VectorStore) -> None:
        """Initialize with an inner embedder and vector store.

        Args:
            inner: The real embedder to delegate uncached texts to.
            store: VectorStore for cached embedding lookup and storage.
        """
        self._inner = inner
        self._store = store
        self.stats: dict[str, int] = {"cache_hits": 0, "cache_misses": 0}

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts, using cache where possible.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            cached = self._store.get(text)
            if cached is not None:
                results[i] = cached
                self.stats["cache_hits"] += 1
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
                self.stats["cache_misses"] += 1

        if uncached_texts:
            new_vecs = self._inner.embed(uncached_texts)
            for idx, text, vec in zip(uncached_indices, uncached_texts, new_vecs, strict=True):
                results[idx] = vec
                self._store.add(text, vec)

        logger.debug(
            "CachedEmbedder: %d hits, %d misses",
            self.stats["cache_hits"],
            self.stats["cache_misses"],
        )
        return results  # type: ignore[return-value]
