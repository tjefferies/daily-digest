"""Tests for per-persona async digest generation runner."""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

from digest.generation.runner import AsyncDigestGenerator
from digest.models.atom import Atom, AtomSource, AtomWorkstreams
from digest.models.digest import DigestSection
from digest.models.persona import DigestPreferences, Persona, ScoringWeights
from digest.models.responses import DigestResponse
from digest.scoring.composite import ScoreBreakdown, ScoredAtom


def _make_atom(
    atom_type: str = "DECISION",
    urgency: str = "medium",
    workstream: str = "chassis",
    channel: str = "#chassis-design",
    thread_ts: str = "1.0",
) -> Atom:
    """Create a test Atom."""
    return Atom(
        atom_id=uuid4(),
        type=atom_type,
        summary="Test atom summary",
        detail="Detailed context",
        source=AtomSource(
            channel=channel,
            thread_ts=thread_ts,
            message_range=[0, 1],
            key_participants=["U001"],
        ),
        workstreams=AtomWorkstreams(originating=workstream),
        urgency=urgency,
        confidence=0.9,
    )


def _make_scored_atom(
    atom: Atom | None = None,
    score: float = 0.7,
    critical: bool = False,
) -> ScoredAtom:
    """Create a test ScoredAtom."""
    a = atom or _make_atom()
    return ScoredAtom(
        atom=a,
        score=score,
        breakdown=ScoreBreakdown(
            workstream_proximity=0.8,
            role_type_alignment=0.7,
            phase_alignment=0.6,
            urgency=0.5,
            social_signal=0.3,
        ),
        critical=critical,
    )


def _make_persona(
    include_broader_context: bool = True,
) -> Persona:
    """Create a test Persona."""
    return Persona(
        user_id="U001",
        name="Maya Chen",
        role_archetype="IC Engineer",
        title="Senior ME",
        workstream_affinities={"chassis": 0.9, "thermal": 0.7},
        phase_context={"chassis": "DVT"},
        scoring_weights=ScoringWeights(
            workstream_proximity=0.30,
            role_type_alignment=0.20,
            phase_alignment=0.20,
            urgency=0.15,
            social_signal=0.15,
        ),
        digest_preferences=DigestPreferences(
            include_broader_context=include_broader_context,
        ),
    )


def _make_section(
    section_type: str = "requires_action",
    title: str = "REQUIRES YOUR ACTION",
) -> DigestSection:
    """Create a test DigestSection."""
    return DigestSection(
        section_type=section_type,
        title=title,
    )


class TestAsyncDigestGenerator:
    """Tests for the async digest generator."""

    async def test_generate_returns_digest_sections(self) -> None:
        """Async generator returns a list of DigestSection objects."""
        client = AsyncMock()
        client.create_structured_message.return_value = DigestResponse(
            sections=[
                _make_section("requires_action", "REQUIRES YOUR ACTION"),
                _make_section("decisions_changes", "DECISIONS & CHANGES"),
            ]
        )
        gen = AsyncDigestGenerator(client)
        scored = [_make_scored_atom()]
        persona = _make_persona()
        sections = await gen.generate(scored, persona)
        assert len(sections) == 2
        assert sections[0].section_type == "requires_action"

    async def test_generate_empty_atoms_returns_empty(self) -> None:
        """Async generator with empty atom list returns empty sections."""
        client = AsyncMock()
        gen = AsyncDigestGenerator(client)
        sections = await gen.generate([], _make_persona())
        assert sections == []

    async def test_generate_updates_stats(self) -> None:
        """Async generator increments persona and section counters."""
        client = AsyncMock()
        client.create_structured_message.return_value = DigestResponse(
            sections=[_make_section("requires_action", "REQUIRES YOUR ACTION")]
        )
        gen = AsyncDigestGenerator(client)
        await gen.generate([_make_scored_atom()], _make_persona())
        assert gen.stats["personas_processed"] == 1
        assert gen.stats["sections_produced"] == 1

    async def test_instructor_failure_returns_empty(self) -> None:
        """Async generator handles exception from structured output."""
        client = AsyncMock()
        client.create_structured_message.side_effect = Exception("Instructor failed")
        gen = AsyncDigestGenerator(client)
        sections = await gen.generate([_make_scored_atom()], _make_persona())
        assert sections == []
