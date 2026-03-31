"""Layer 1: Ingestion — parse fixture data into typed message streams.

Converts raw JSON dicts from the FixtureStore into validated, time-ordered
SlackMessage objects that all downstream pipeline layers consume.
"""

from evercurrent.ingestion.loader import load_message_stream

__all__ = ["load_message_stream"]
