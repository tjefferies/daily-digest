"""Tests for the LLM extraction system prompts (two-stage).

Validates that the coarse and enrichment prompts contain the
critical instructions and schema fields.
"""

from digest.extraction.prompt import build_coarse_prompt, build_enrichment_prompt


class TestCoarsePromptContainsCriticalInstructions:
    """The coarse prompt must encode extraction rules."""

    def test_extract_conclusions_not_discussions(self) -> None:
        """Prompt instructs to extract conclusions, not debate summaries."""
        prompt = build_coarse_prompt()
        assert "conclusion" in prompt.lower()

    def test_contains_atom_types(self) -> None:
        """Prompt includes all 8 AtomType values."""
        prompt = build_coarse_prompt()
        for atom_type in [
            "DECISION",
            "SPEC_CHANGE",
            "ACTION_ITEM",
            "BLOCKER",
            "RISK",
            "TEST_RESULT",
            "STATUS_UPDATE",
            "QUESTION",
        ]:
            assert atom_type in prompt, f"Missing: {atom_type}"

    def test_prompt_is_nonempty(self) -> None:
        """Prompt returns a non-empty string."""
        prompt = build_coarse_prompt()
        assert len(prompt) > 100


class TestEnrichmentPrompt:
    """The enrichment prompt must encode metadata assignment rules."""

    def test_flag_implicit_decisions(self) -> None:
        """Prompt instructs to flag implicit decisions."""
        prompt = build_enrichment_prompt()
        assert "implicit" in prompt.lower()

    def test_tag_affected_workstreams(self) -> None:
        """Prompt instructs to tag affected workstreams."""
        prompt = build_enrichment_prompt()
        assert "affected" in prompt.lower()

    def test_contains_urgency_levels(self) -> None:
        """Prompt includes urgency level options."""
        prompt = build_enrichment_prompt()
        for level in ["low", "medium", "high", "critical"]:
            assert level in prompt.lower()

    def test_contains_phase_options(self) -> None:
        """Prompt includes valid Phase values."""
        prompt = build_enrichment_prompt()
        for phase in ["Concept", "EVT", "DVT", "PVT", "MP"]:
            assert phase in prompt
