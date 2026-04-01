"""Tests for the DigestSection Pydantic model."""

import pytest
from pydantic import ValidationError

from evercurrent.models.digest import (
    Digest,
    DigestItem,
    DigestSection,
    SectionType,
)


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
    def sample_item(self) -> DigestItem:
        """Return a sample DigestItem for section tests."""
        return DigestItem(
            headline="Team agreed to switch housing material",
            context="Switching from aluminum to magnesium to meet weight target.",
            source_channel="#chassis-design",
            atom_id="550e8400-e29b-41d4-a716-446655440000",
        )

    def test_valid_section(self, sample_item: DigestItem) -> None:
        """Verify a DigestSection accepts items and preserves fields."""
        section = DigestSection(
            section_type="requires_action",
            title="Requires Your Action",
            items=[sample_item],
        )
        assert section.section_type == "requires_action"
        assert len(section.items) == 1
        assert section.items[0].headline == "Team agreed to switch housing material"

    def test_empty_section(self) -> None:
        """Verify a DigestSection can be created with no items."""
        section = DigestSection(
            section_type="broader_context",
            title="Broader Team Context",
            items=[],
        )
        assert section.items == []


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
                ),
                DigestSection(
                    section_type="decisions_changes",
                    title="Decisions & Changes",
                ),
                DigestSection(
                    section_type="progress_risks",
                    title="Progress & Risks",
                ),
                DigestSection(
                    section_type="broader_context",
                    title="Broader Team Context",
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
            )
