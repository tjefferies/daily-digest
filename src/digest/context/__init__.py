"""Layer 3: Context Backbone.

Provides the world model that the relevance scoring layer queries:
team roster with role archetypes, workstream registry, phase vectors,
and persona definitions.
"""

from digest.context.personas import DEMO_PERSONAS, get_persona
from digest.context.phases import PhaseVector
from digest.context.roster import RosterEntry, TeamRosterService
from digest.context.workstreams import WorkstreamRegistry

__all__ = [
    "DEMO_PERSONAS",
    "PhaseVector",
    "RosterEntry",
    "TeamRosterService",
    "WorkstreamRegistry",
    "get_persona",
]
