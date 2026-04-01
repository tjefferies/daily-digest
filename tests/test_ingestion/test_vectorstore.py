"""Tests for FAISS vectorstore: persist and load embeddings from disk."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from evercurrent.ingestion.vectorstore import VectorStore


class TestVectorStore:
    """Tests for the FAISS-backed VectorStore."""

    def test_add_and_lookup(self) -> None:
        """Added embeddings are retrievable by text hash."""
        store = VectorStore(dim=3)
        store.add("hello world", [1.0, 0.0, 0.0])
        result = store.get("hello world")
        assert result is not None
        assert len(result) == 3
        assert result[0] == pytest.approx(1.0)

    def test_get_missing_returns_none(self) -> None:
        """Looking up a text not in the store returns None."""
        store = VectorStore(dim=3)
        assert store.get("not here") is None

    def test_contains(self) -> None:
        """__contains__ checks if a text key exists."""
        store = VectorStore(dim=3)
        store.add("exists", [1.0, 0.0, 0.0])
        assert "exists" in store
        assert "missing" not in store

    def test_save_and_load(self, tmp_path: Path) -> None:
        """Store persists to disk and loads back with same data."""
        store = VectorStore(dim=3)
        store.add("text_a", [1.0, 0.0, 0.0])
        store.add("text_b", [0.0, 1.0, 0.0])

        save_path = tmp_path / "test.index"
        store.save(save_path)

        loaded = VectorStore.load(save_path)
        assert loaded.get("text_a") is not None
        assert loaded.get("text_a")[0] == pytest.approx(1.0)
        assert loaded.get("text_b") is not None
        assert loaded.get("text_b")[1] == pytest.approx(1.0)
        assert loaded.get("missing") is None

    def test_load_nonexistent_returns_empty(self, tmp_path: Path) -> None:
        """Loading from a nonexistent path returns an empty store."""
        store = VectorStore.load(tmp_path / "nope.index", dim=3)
        assert store.get("anything") is None

    def test_len(self) -> None:
        """len() returns the number of stored embeddings."""
        store = VectorStore(dim=3)
        assert len(store) == 0
        store.add("a", [1.0, 0.0, 0.0])
        store.add("b", [0.0, 1.0, 0.0])
        assert len(store) == 2

    def test_add_duplicate_key_overwrites(self) -> None:
        """Adding the same text key overwrites the embedding."""
        store = VectorStore(dim=3)
        store.add("key", [1.0, 0.0, 0.0])
        store.add("key", [0.0, 1.0, 0.0])
        result = store.get("key")
        assert result is not None
        assert result[1] == pytest.approx(1.0)
        assert len(store) == 1
