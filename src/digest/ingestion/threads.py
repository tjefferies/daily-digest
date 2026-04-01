"""Thread reconstruction Pass 1: structural grouping by thread_ts.

Groups SlackMessage objects into ThreadBundle objects based on their
thread_ts field. A root message plus all replies forms one bundle.
"""

from collections import defaultdict

from pydantic import BaseModel, Field

from digest.dataset.schema import SlackMessage


class ThreadBundle(BaseModel):
    """A thread consisting of a root message and its replies.

    Attributes:
        root_message: The thread-starting message.
        replies: Chronologically ordered replies to the root.
    """

    root_message: SlackMessage
    replies: list[SlackMessage] = Field(default_factory=list)


def group_by_thread(messages: list[SlackMessage]) -> list[ThreadBundle]:
    """Group messages into ThreadBundles by thread_ts.

    Messages with thread_ts == None or thread_ts == message_ts are
    roots. Messages whose thread_ts references a missing root use
    the earliest message in the group as the synthetic root.

    Args:
        messages: Flat list of SlackMessage objects.

    Returns:
        List of ThreadBundle objects sorted by root message_ts.
    """
    if not messages:
        return []

    groups: dict[str, list[SlackMessage]] = defaultdict(list)
    for msg in messages:
        key = msg.thread_ts if msg.thread_ts else msg.message_ts
        groups[key].append(msg)

    bundles: list[ThreadBundle] = []
    for thread_ts, thread_msgs in groups.items():
        sorted_msgs = sorted(thread_msgs, key=lambda m: m.message_ts)
        root = None
        replies = []
        for m in sorted_msgs:
            if m.message_ts == thread_ts:
                root = m
            else:
                replies.append(m)
        if root is None:
            root = sorted_msgs[0]
            replies = sorted_msgs[1:]
        bundles.append(ThreadBundle(root_message=root, replies=replies))

    return sorted(bundles, key=lambda b: b.root_message.message_ts)
