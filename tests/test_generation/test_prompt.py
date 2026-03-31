"""Tests for digest generation prompt design."""

from __future__ import annotations

from evercurrent.generation.prompt import build_generation_prompt


class TestGenerationPromptTone:
    """Tests for briefing tone instructions per section 7.2."""

    def test_briefing_not_newsletter(self) -> None:
        """Prompt instructs briefing tone, not newsletter."""
        prompt = build_generation_prompt()
        assert "briefing" in prompt.lower()
        assert "newsletter" in prompt.lower()

    def test_terse_specific_actionable(self) -> None:
        """Prompt requires terse, specific, actionable language."""
        prompt = build_generation_prompt()
        assert "terse" in prompt.lower()
        assert "specific" in prompt.lower()

    def test_information_density(self) -> None:
        """Prompt emphasizes information density."""
        prompt = build_generation_prompt()
        assert "information" in prompt.lower() and "density" in prompt.lower()


class TestGenerationPromptFormat:
    """Tests for scannable format instructions."""

    def test_bold_headline(self) -> None:
        """Prompt requires bold headline per item."""
        prompt = build_generation_prompt()
        assert "bold" in prompt.lower()
        assert "headline" in prompt.lower()

    def test_context_sentence(self) -> None:
        """Prompt requires 1-2 sentence context."""
        prompt = build_generation_prompt()
        assert "1" in prompt and "2" in prompt
        assert "sentence" in prompt.lower() or "context" in prompt.lower()

    def test_source_link(self) -> None:
        """Prompt requires source reference."""
        prompt = build_generation_prompt()
        assert "source" in prompt.lower()

    def test_scannable_in_30_seconds(self) -> None:
        """Prompt references 30-second scannability."""
        prompt = build_generation_prompt()
        assert "30" in prompt
        assert "scan" in prompt.lower()


class TestGenerationPromptJudgment:
    """Tests for no-editorializing rule."""

    def test_no_editorializing(self) -> None:
        """Prompt explicitly forbids editorializing."""
        prompt = build_generation_prompt()
        assert "editorialize" in prompt.lower() or "editorial" in prompt.lower()

    def test_no_opinions(self) -> None:
        """Prompt forbids opinions and recommendations."""
        prompt = build_generation_prompt()
        assert "opinion" in prompt.lower()

    def test_no_unsolicited_recommendations(self) -> None:
        """Prompt forbids unsolicited recommendations."""
        prompt = build_generation_prompt()
        assert "recommend" in prompt.lower()


class TestGenerationPromptSections:
    """Tests for four-section digest structure."""

    def test_requires_action_section(self) -> None:
        """Prompt defines Requires Your Action section."""
        prompt = build_generation_prompt()
        assert "requires your action" in prompt.lower() or "requires_action" in prompt.lower()

    def test_decisions_changes_section(self) -> None:
        """Prompt defines Decisions and Changes section."""
        prompt = build_generation_prompt()
        assert "decisions" in prompt.lower() and "changes" in prompt.lower()

    def test_progress_risks_section(self) -> None:
        """Prompt defines Progress and Risks section."""
        prompt = build_generation_prompt()
        assert "progress" in prompt.lower() and "risks" in prompt.lower()

    def test_broader_context_section(self) -> None:
        """Prompt defines Broader Context section."""
        prompt = build_generation_prompt()
        assert "broader context" in prompt.lower()

    def test_requires_action_max_5_items(self) -> None:
        """Requires Action section is capped at 5 items."""
        prompt = build_generation_prompt()
        # The prompt should mention the 5-item cap
        assert "5" in prompt

    def test_four_sections_defined(self) -> None:
        """All four section types are mentioned."""
        prompt = build_generation_prompt().lower()
        sections = [
            "requires your action",
            "decisions",
            "progress",
            "broader context",
        ]
        for section in sections:
            assert section in prompt, f"Missing section: {section}"


class TestGenerationPromptStructure:
    """Tests for prompt structural requirements."""

    def test_persona_context_instruction(self) -> None:
        """Prompt instructs to use persona context."""
        prompt = build_generation_prompt()
        assert "persona" in prompt.lower()

    def test_atom_types_referenced(self) -> None:
        """Prompt references atom types for section routing."""
        prompt = build_generation_prompt()
        assert "DECISION" in prompt
        assert "SPEC_CHANGE" in prompt
        assert "BLOCKER" in prompt
        assert "RISK" in prompt

    def test_prompt_is_substantial(self) -> None:
        """Prompt is at least 500 chars to encode all rules."""
        prompt = build_generation_prompt()
        assert len(prompt) > 500

    def test_json_output_format(self) -> None:
        """Prompt specifies JSON output format."""
        prompt = build_generation_prompt()
        assert "json" in prompt.lower()
