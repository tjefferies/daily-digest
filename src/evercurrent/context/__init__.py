"""Layer 3: Context Backbone.

Provides the world model that the relevance scoring layer queries:
team roster with role archetypes, workstream registry, phase vectors,
and persona definitions.
"""

from evercurrent.context.roster import RosterEntry, TeamRosterService

__all__ = [
    "RosterEntry",
    "TeamRosterService",
]
