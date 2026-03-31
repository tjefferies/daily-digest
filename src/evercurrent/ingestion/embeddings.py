"""Embedding protocol and utilities for semantic continuation matching.

Defines the Embedder protocol for dependency injection and provides
a cosine similarity function for comparing text embeddings. The
SentenceTransformerEmbedder wraps sentence-transformers for local
inference.
"""

from __future__ import annotations

import math
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Protocol for text embedding providers.

    Implementations produce fixed-dimensional vectors from text input.
    The protocol enables dependency injection: production code uses
    SentenceTransformerEmbedder, tests use deterministic mocks.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into dense vectors.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors, one per input text.
        """
        ...


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Args:
        vec_a: First embedding vector.
        vec_b: Second embedding vector.

    Returns:
        Cosine similarity in [-1.0, 1.0]. Returns 0.0 if either
        vector has zero magnitude.
    """
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


class SentenceTransformerEmbedder:
    """Embedder backed by sentence-transformers for local inference.

    Uses all-MiniLM-L6-v2 by default (~80MB, <10ms per embed on CPU).
    The model is loaded lazily on first embed() call.

    Attributes:
        model_name: HuggingFace model identifier.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize with a model name.

        Args:
            model_name: HuggingFace sentence-transformers model ID.
        """
        self._model_name = model_name
        self._model: object | None = None

    def _load_model(self) -> object:
        """Lazy-load the sentence-transformers model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using the sentence-transformer model.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors (384-dim for MiniLM).
        """
        model = self._load_model()
        embeddings = model.encode(texts)  # type: ignore[union-attr]
        return embeddings.tolist()  # type: ignore[union-attr]
