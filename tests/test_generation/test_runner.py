"""Tests for per-persona digest generation runner."""

from __future__ import annotations

import json
from unittest.mock import MagicMock
from uuid import uuid4

from anthropic.types import TextBlock

from evercurrent.generation.runner import DigestGenerator
from evercurrent.models.atom import Atom, AtomSource, AtomWorkstreams
from evercurrent.models.persona import DigestPreferences, Persona, ScoringWeights
from evercurrent.scoring.composite import ScoreBreakdown, ScoredAtom


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


def _mock_api_response(sections: list[dict]) -> MagicMock:  # noqa: ANN401
    """Create a mock Anthropic API response with given sections."""
    response_json = json.dumps({"sections": sections})
    mock_response = MagicMock()
    mock_response.content = [TextBlock(type="text", text=response_json)]
    return mock_response


def _valid_section(
    section_type: str = "requires_action",
    title: str = "REQUIRES YOUR ACTION",
) -> dict:
    """Create a valid section dict for mock responses."""
    return {
        "section_type": section_type,
        "title": title,
        "items": [
            {
                "headline": "Test headline",
                "context": "Test context sentence.",
                "source_channel": "#chassis-design",
                "source_thread_ts": "1.0",
                "atom_id": str(uuid4()),
            },
        ],
    }


class TestDigestGeneratorInit:
    """Tests for DigestGenerator initialization."""

    def test_init_stores_client(self) -> None:
        """Generator stores the Anthropic client."""
        client = MagicMock()
        gen = DigestGenerator(client)
        assert gen._client is client  # noqa: SLF001

    def test_init_has_stats(self) -> None:
        """Generator initializes stats tracking."""
        gen = DigestGenerator(MagicMock())
        assert gen.stats["personas_processed"] == 0
        assert gen.stats["sections_produced"] == 0


class TestDigestGeneratorGenerate:
    """Tests for the generate method."""

    def test_generate_returns_digest_sections(self) -> None:
        """Generate returns a list of DigestSection objects."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response(
            [
                _valid_section("requires_action", "REQUIRES YOUR ACTION"),
                _valid_section("decisions_changes", "DECISIONS & CHANGES"),
                _valid_section("progress_risks", "PROGRESS & RISKS"),
                _valid_section("broader_context", "BROADER CONTEXT"),
            ]
        )
        gen = DigestGenerator(client)
        scored = [_make_scored_atom()]
        persona = _make_persona()
        sections = gen.generate(scored, persona)
        assert len(sections) == 4
        assert sections[0].section_type == "requires_action"

    def test_generate_passes_persona_context(self) -> None:
        """Generate includes persona context in the API call."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response(
            [
                _valid_section(),
            ]
        )
        gen = DigestGenerator(client)
        persona = _make_persona()
        gen.generate([_make_scored_atom()], persona)
        call_args = client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]
        assert "Maya Chen" in user_content
        assert "IC Engineer" in user_content

    def test_generate_passes_scored_atoms(self) -> None:
        """Generate includes scored atom data in the API call."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response(
            [
                _valid_section(),
            ]
        )
        gen = DigestGenerator(client)
        atom = _make_atom(atom_type="BLOCKER")
        scored = [_make_scored_atom(atom=atom, score=0.9, critical=True)]
        gen.generate(scored, _make_persona())
        call_args = client.messages.create.call_args
        user_content = call_args.kwargs["messages"][0]["content"]
        assert "BLOCKER" in user_content
        assert "0.9" in user_content

    def test_generate_updates_stats(self) -> None:
        """Generate increments persona and section counters."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response(
            [
                _valid_section("requires_action", "REQUIRES YOUR ACTION"),
                _valid_section("decisions_changes", "DECISIONS & CHANGES"),
            ]
        )
        gen = DigestGenerator(client)
        gen.generate([_make_scored_atom()], _make_persona())
        assert gen.stats["personas_processed"] == 1
        assert gen.stats["sections_produced"] == 2

    def test_generate_empty_atoms_returns_empty(self) -> None:
        """Generate with empty atom list returns empty sections."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response([])
        gen = DigestGenerator(client)
        sections = gen.generate([], _make_persona())
        assert sections == []


class TestBroaderContextFiltering:
    """Tests for broader context preference filtering."""

    def test_broader_context_excluded_when_disabled(self) -> None:
        """Broader context section is filtered when preference is false."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response(
            [
                _valid_section("requires_action", "REQUIRES YOUR ACTION"),
                _valid_section("broader_context", "BROADER CONTEXT"),
            ]
        )
        gen = DigestGenerator(client)
        persona = _make_persona(include_broader_context=False)
        sections = gen.generate([_make_scored_atom()], persona)
        section_types = [s.section_type for s in sections]
        assert "broader_context" not in section_types

    def test_broader_context_included_when_enabled(self) -> None:
        """Broader context section is kept when preference is true."""
        client = MagicMock()
        client.messages.create.return_value = _mock_api_response(
            [
                _valid_section("requires_action", "REQUIRES YOUR ACTION"),
                _valid_section("broader_context", "BROADER CONTEXT"),
            ]
        )
        gen = DigestGenerator(client)
        persona = _make_persona(include_broader_context=True)
        sections = gen.generate([_make_scored_atom()], persona)
        section_types = [s.section_type for s in sections]
        assert "broader_context" in section_types


class TestResponseParsing:
    """Tests for API response parsing."""

    def test_invalid_json_returns_empty(self) -> None:
        """Invalid JSON response returns empty list."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [TextBlock(type="text", text="not json")]
        client.messages.create.return_value = mock_response
        gen = DigestGenerator(client)
        sections = gen.generate([_make_scored_atom()], _make_persona())
        assert sections == []

    def test_missing_sections_key_returns_empty(self) -> None:
        """Response without 'sections' key returns empty list."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [TextBlock(type="text", text='{"data": []}')]
        client.messages.create.return_value = mock_response
        gen = DigestGenerator(client)
        sections = gen.generate([_make_scored_atom()], _make_persona())
        assert sections == []

    def test_non_text_block_returns_empty(self) -> None:
        """Non-TextBlock response returns empty list."""
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(spec=[])]
        client.messages.create.return_value = mock_response
        gen = DigestGenerator(client)
        sections = gen.generate([_make_scored_atom()], _make_persona())
        assert sections == []
