"""Layer 1: Ingestion — parse fixture data into typed message streams.

Converts raw JSON dicts from the FixtureStore into validated, time-ordered
SlackMessage objects that all downstream pipeline layers consume.
"""

from evercurrent.ingestion.continuations import ContinuationMatch, detect_continuations
from evercurrent.ingestion.loader import load_message_stream
from evercurrent.ingestion.threads import ThreadBundle, group_by_thread

__all__ = [
    "ContinuationMatch",
    "ThreadBundle",
    "detect_continuations",
    "group_by_thread",
    "load_message_stream",
]
