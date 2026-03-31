"""Tests for the DigestSection Pydantic model."""

import pytest
from pydantic import ValidationError

from evercurrent.models.atom import Atom
from evercurrent.models.digest import Digest, DigestSection, SectionType


class TestSectionType:
    """Tests for DigestSection type literals."""

    def test_all_four_sections_exist(self) -> None:
        """Verify all 4 digest section types are defined."""
        expected = {
            "requires_action",
            "decisions_changes",
            "progress_risks",
            "broader_context",
        }
        assert set(SectionType.__args__) == expected


class TestDigestSection:
    """Tests for DigestSection model."""

    @pytest.fixture
    def sample_atom(self) -> Atom:
        """Return a sample Atom for digest section tests."""
        return Atom(
            atom_id="550e8400-e29b-41d4-a716-446655440000",
            type="DECISION",
            summary="Team agreed to switch housing material",
            detail="Switching from aluminum to magnesium to meet weight target.",
            source={
                "channel": "#chassis-design",
                "thread_ts": "1234567890.123456",
                "message_range": [1, 10],
                "key_participants": ["@maya"],
            },
            workstreams={"originating": "chassis", "affected": ["supply-chain"]},
            urgency="high",
            confidence=0.95,
            implicit_decision=False,
            phase_relevance=["DVT"],
        )

    def test_valid_section(self, sample_atom: Atom) -> None:
        """Verify a DigestSection accepts atoms and preserves fields."""
        section = DigestSection(
            section_type="requires_action",
            title="Requires Your Action",
            atoms=[sample_atom],
        )
        assert section.section_type == "requires_action"
        assert len(section.atoms) == 1
        assert section.atoms[0].type == "DECISION"

    def test_empty_section(self) -> None:
        """Verify a DigestSection can be created with no atoms."""
        section = DigestSection(
            section_type="broader_context",
            title="Broader Team Context",
            atoms=[],
        )
        assert section.atoms == []


class TestDigest:
    """Tests for the top-level Digest model."""

    def test_digest_has_four_sections(self) -> None:
        """Verify a Digest can hold all four section types."""
        digest = Digest(
            persona_id="U02ABCDEF",
            sections=[
                DigestSection(
                    section_type="requires_action",
                    title="Requires Your Action",
                    atoms=[],
                ),
                DigestSection(
                    section_type="decisions_changes",
                    title="Decisions & Changes",
                    atoms=[],
                ),
                DigestSection(
                    section_type="progress_risks",
                    title="Progress & Risks",
                    atoms=[],
                ),
                DigestSection(
                    section_type="broader_context",
                    title="Broader Team Context",
                    atoms=[],
                ),
            ],
        )
        assert len(digest.sections) == 4
        assert digest.persona_id == "U02ABCDEF"

    def test_digest_rejects_invalid_section_type(self) -> None:
        """Verify DigestSection rejects a section_type not in the literal."""
        with pytest.raises(ValidationError):
            DigestSection(
                section_type="invalid_section",
                title="Bad",
                atoms=[],
            )
