"""Layer 1: Ingestion - parse fixture data into typed message streams.

Converts raw JSON dicts from the FixtureStore into validated, time-ordered
SlackMessage objects that all downstream pipeline layers consume. Thread
reconstruction uses a hybrid keyword + semantic approach for continuation
detection.
"""

from evercurrent.ingestion.context_window import ContextWindow, assemble_context_windows
from evercurrent.ingestion.continuations import ContinuationMatch, detect_continuations
from evercurrent.ingestion.embeddings import (
    Embedder,
    SentenceTransformerEmbedder,
    cosine_similarity,
)
from evercurrent.ingestion.loader import load_message_stream
from evercurrent.ingestion.threads import ThreadBundle, group_by_thread
from evercurrent.ingestion.vectorstore import VectorStore

__all__ = [
    "ContinuationMatch",
    "ContextWindow",
    "Embedder",
    "SentenceTransformerEmbedder",
    "ThreadBundle",
    "VectorStore",
    "assemble_context_windows",
    "cosine_similarity",
    "detect_continuations",
    "group_by_thread",
    "load_message_stream",
]
