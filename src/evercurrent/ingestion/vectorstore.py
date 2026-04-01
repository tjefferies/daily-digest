"""Persistent FAISS vector store for caching text embeddings.

Stores text → embedding mappings in a FAISS IndexFlatIP with a
parallel key mapping for O(1) lookup by text content. Persists
the FAISS index and key map to disk as two files (.index + .keys).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import faiss  # type: ignore[import-untyped]
import numpy as np

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class VectorStore:
    """Persistent embedding cache backed by FAISS IndexFlatIP.

    Maps text content to embedding vectors via a FAISS index.
    Supports save/load for persistence across pipeline runs.

    Args:
        dim: Dimensionality of embedding vectors.
    """

    def __init__(self, dim: int = 384) -> None:
        """Initialize an empty vector store.

        Args:
            dim: Dimensionality of embedding vectors.
        """
        self._dim = dim
        self._index: faiss.IndexFlatIP = faiss.IndexFlatIP(dim)
        self._keys: list[str] = []
        self._key_to_idx: dict[str, int] = {}

    def add(self, text: str, vector: list[float]) -> None:
        """Add or overwrite an embedding for a text key.

        Args:
            text: The original text content.
            vector: The embedding vector.
        """
        vec = np.array([vector], dtype=np.float32)
        faiss.normalize_L2(vec)
        if text in self._key_to_idx:
            idx = self._key_to_idx[text]
            self._index.reconstruct(idx)
            # FAISS IndexFlatIP doesn't support in-place update,
            # so we rebuild the index without the old entry.
            self._rebuild_without(idx)
        self._key_to_idx[text] = self._index.ntotal
        self._keys.append(text)
        self._index.add(vec)

    def _rebuild_without(self, remove_idx: int) -> None:
        """Rebuild the index excluding one entry.

        Args:
            remove_idx: Index position to exclude.
        """
        vecs = []
        new_keys = []
        for i, key in enumerate(self._keys):
            if i == remove_idx:
                continue
            vec = np.zeros(self._dim, dtype=np.float32)
            self._index.reconstruct(i, vec)
            vecs.append(vec)
            new_keys.append(key)
        self._index.reset()
        if vecs:
            self._index.add(np.stack(vecs))
        self._keys = new_keys
        self._key_to_idx = {k: i for i, k in enumerate(self._keys)}

    def get(self, text: str) -> list[float] | None:
        """Retrieve the embedding for a text, or None if not cached.

        Args:
            text: The original text content.

        Returns:
            The cached embedding vector, or None.
        """
        idx = self._key_to_idx.get(text)
        if idx is None:
            return None
        vec = np.zeros(self._dim, dtype=np.float32)
        self._index.reconstruct(idx, vec)
        return vec.tolist()

    def __contains__(self, text: str) -> bool:
        """Check if a text has a cached embedding."""
        return text in self._key_to_idx

    def __len__(self) -> int:
        """Return the number of cached embeddings."""
        return self._index.ntotal

    def save(self, path: Path) -> None:
        """Persist the FAISS index and key map to disk.

        Writes two files: path (FAISS index) and path.with_suffix('.keys')
        (JSON key mapping).

        Args:
            path: File path for the FAISS index.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(path))
        keys_path = path.with_suffix(".keys")
        keys_path.write_text(json.dumps(self._keys), encoding="utf-8")
        logger.info("VectorStore saved: %d embeddings to %s", len(self), path)

    @classmethod
    def load(cls, path: Path, dim: int = 384) -> VectorStore:
        """Load a store from disk, or return an empty store if not found.

        Args:
            path: File path of the FAISS index.
            dim: Default dimensionality if creating a new store.

        Returns:
            Loaded VectorStore, or empty if file does not exist.
        """
        if not path.exists():
            logger.info("VectorStore not found at %s, starting empty", path)
            return cls(dim=dim)

        store = cls.__new__(cls)
        store._index = faiss.read_index(str(path))
        store._dim = store._index.d

        keys_path = path.with_suffix(".keys")
        if keys_path.exists():
            store._keys = json.loads(keys_path.read_text(encoding="utf-8"))
        else:
            store._keys = []
        store._key_to_idx = {k: i for i, k in enumerate(store._keys)}
        logger.info("VectorStore loaded: %d embeddings from %s", len(store), path)
        return store
