"""Message loader: parse fixture dicts into a typed SlackMessage stream.

This is the ingestion boundary - all downstream layers work with
SlackMessage objects, not raw JSON dicts.
"""

from digest.dataset.schema import SlackMessage
from digest.fixtures import FixtureStore


def load_message_stream(store: FixtureStore) -> list[SlackMessage]:
    """Load messages from a FixtureStore as typed, time-ordered SlackMessages.

    Args:
        store: The fixture store containing raw message dicts.

    Returns:
        List of SlackMessage objects sorted by message_ts ascending.
    """
    raw = store.get_messages()
    messages = [SlackMessage(**msg) for msg in raw]
    return sorted(messages, key=lambda m: m.message_ts)
