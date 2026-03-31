"""Layer 3: Context Backbone.

Provides the world model that the relevance scoring layer queries:
team roster with role archetypes, workstream registry, phase vectors,
and persona definitions.
"""

from evercurrent.context.personas import DEMO_PERSONAS, get_persona
from evercurrent.context.phases import PhaseVector
from evercurrent.context.roster import RosterEntry, TeamRosterService
from evercurrent.context.workstreams import WorkstreamRegistry

__all__ = [
    "DEMO_PERSONAS",
    "PhaseVector",
    "RosterEntry",
    "TeamRosterService",
    "WorkstreamRegistry",
    "get_persona",
]
