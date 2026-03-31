"""Tests for the LLM extraction system prompt.

Validates that the extraction prompt contains the three critical
instructions from section 4.3 and includes the Atom JSON schema.
"""

from evercurrent.extraction.prompt import build_extraction_prompt


class TestPromptContainsCriticalInstructions:
    """The prompt must encode three extraction rules from section 4.3."""

    def test_extract_conclusions_not_discussions(self) -> None:
        """Prompt instructs to extract conclusions, not debate summaries."""
        prompt = build_extraction_prompt()
        assert "conclusion" in prompt.lower()
        assert "not" in prompt.lower() and "discussion" in prompt.lower()

    def test_flag_implicit_decisions(self) -> None:
        """Prompt instructs to flag implicit decisions with lower confidence."""
        prompt = build_extraction_prompt()
        assert "implicit" in prompt.lower()
        assert "decision" in prompt.lower()

    def test_tag_affected_workstreams_beyond_originating(self) -> None:
        """Prompt instructs to tag affected workstreams, not just originating."""
        prompt = build_extraction_prompt()
        assert "affected" in prompt.lower()
        assert "workstream" in prompt.lower()


class TestPromptIncludesAtomSchema:
    """The prompt must include the full Atom JSON schema."""

    def test_contains_atom_type_enum(self) -> None:
        """Prompt includes all 8 AtomType values."""
        prompt = build_extraction_prompt()
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
            assert atom_type in prompt, f"Missing AtomType: {atom_type}"

    def test_contains_urgency_levels(self) -> None:
        """Prompt includes urgency level options."""
        prompt = build_extraction_prompt()
        for level in ["low", "medium", "high", "critical"]:
            assert level in prompt.lower(), f"Missing urgency: {level}"

    def test_contains_phase_options(self) -> None:
        """Prompt includes valid Phase values."""
        prompt = build_extraction_prompt()
        for phase in ["Concept", "EVT", "DVT", "PVT", "MP"]:
            assert phase in prompt, f"Missing phase: {phase}"

    def test_contains_json_structure_markers(self) -> None:
        """Prompt includes JSON schema field names."""
        prompt = build_extraction_prompt()
        for field in [
            "atom_id",
            "summary",
            "detail",
            "source",
            "workstreams",
            "urgency",
            "confidence",
            "implicit_decision",
            "phase_relevance",
        ]:
            assert field in prompt, f"Missing schema field: {field}"

    def test_contains_source_subfields(self) -> None:
        """Prompt includes AtomSource subfield names."""
        prompt = build_extraction_prompt()
        for field in ["channel", "thread_ts", "message_range", "key_participants"]:
            assert field in prompt, f"Missing source field: {field}"


class TestPromptStructure:
    """Prompt should be well-structured for LLM consumption."""

    def test_prompt_is_nonempty_string(self) -> None:
        """Prompt returns a non-empty string."""
        prompt = build_extraction_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 200

    def test_prompt_requests_json_output(self) -> None:
        """Prompt explicitly requests JSON output."""
        prompt = build_extraction_prompt()
        assert "json" in prompt.lower()
