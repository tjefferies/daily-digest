"""Tests for .env.sample file completeness and correctness.

Verifies that the .env.sample file at the repo root documents every
environment variable referenced by the codebase - including those
read implicitly by third-party SDKs.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ENV_SAMPLE = _REPO_ROOT / ".env.sample"

# The canonical list of env vars used by this project.
# Each tuple: (VAR_NAME, required: bool)
_EXPECTED_VARS: list[tuple[str, bool]] = [
    # LLM provider API keys (read implicitly by SDK constructors)
    ("ANTHROPIC_API_KEY", True),
    ("OPENAI_API_KEY", False),
    ("GOOGLE_API_KEY", False),
    # Neo4j knowledge graph connection
    ("NEO4J_URI", True),
    ("NEO4J_USER", True),
    ("NEO4J_PASSWORD", True),
]


def _parse_env_sample() -> dict[str, str]:
    """Parse .env.sample into a dict of VAR_NAME -> raw line value.

    Returns:
        Dict mapping variable names to their placeholder values.
    """
    result: dict[str, str] = {}
    for line in _ENV_SAMPLE.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "=" in stripped:
            key, _, value = stripped.partition("=")
            result[key.strip()] = value.strip()
    return result


class TestEnvSampleExists:
    """Verify .env.sample file exists at repo root."""

    def test_file_exists(self) -> None:
        """.env.sample must exist at the repository root."""
        assert _ENV_SAMPLE.exists(), f"Missing {_ENV_SAMPLE}"

    def test_file_is_not_empty(self) -> None:
        """.env.sample must not be empty."""
        assert _ENV_SAMPLE.stat().st_size > 0


class TestEnvSampleContent:
    """Verify .env.sample documents all required environment variables."""

    def test_contains_all_expected_vars(self) -> None:
        """Every expected env var must appear in .env.sample."""
        env_vars = _parse_env_sample()
        for var_name, _required in _EXPECTED_VARS:
            assert var_name in env_vars, f"{var_name} missing from .env.sample"

    def test_required_vars_have_placeholder(self) -> None:
        """Required vars must have a non-empty placeholder value."""
        env_vars = _parse_env_sample()
        for var_name, required in _EXPECTED_VARS:
            if required and var_name in env_vars:
                assert env_vars[var_name], f"{var_name} has empty placeholder"

    def test_no_real_secrets(self) -> None:
        """.env.sample must not contain real API keys."""
        content = _ENV_SAMPLE.read_text()
        # Real Anthropic keys start with sk-ant-
        assert "sk-ant-" not in content, ".env.sample contains a real Anthropic key"
        # Real OpenAI keys start with sk-
        for line in content.splitlines():
            if line.strip().startswith("OPENAI_API_KEY"):
                _, _, val = line.partition("=")
                val = val.strip().strip('"').strip("'")
                assert not val.startswith("sk-"), ".env.sample contains a real OpenAI key"

    def test_has_comments(self) -> None:
        """.env.sample should include comments explaining the variables."""
        content = _ENV_SAMPLE.read_text()
        comment_lines = [line for line in content.splitlines() if line.strip().startswith("#")]
        assert len(comment_lines) >= 3, ".env.sample should have descriptive comments"

    def test_docker_compose_vars_covered(self) -> None:
        """Every env var in docker-compose.yml must appear in .env.sample."""
        dc_path = _REPO_ROOT / "docker-compose.yml"
        if not dc_path.exists():
            return
        env_vars = _parse_env_sample()
        import re

        dc_content = dc_path.read_text()
        # Match ${VAR_NAME:-...} and ${VAR_NAME} patterns
        dc_vars = set(re.findall(r"\$\{(\w+?)(?::-.*)?\}", dc_content))
        for var in dc_vars:
            assert var in env_vars, (
                f"{var} referenced in docker-compose.yml but missing from .env.sample"
            )
