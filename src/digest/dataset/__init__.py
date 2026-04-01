"""Synthetic dataset schemas and fixtures for EverCurrent.

Defines the data contracts between the synthetic Slack dataset
and the ingestion layer: raw message format, channel registry,
and team roster.
"""

from digest.dataset.messages import load_messages
from digest.dataset.schema import (
    CHANNELS,
    SlackMessage,
    SlackReaction,
    TeamMember,
    TeamRoster,
)

__all__ = [
    "CHANNELS",
    "SlackMessage",
    "SlackReaction",
    "TeamMember",
    "TeamRoster",
    "load_messages",
]
