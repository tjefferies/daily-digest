"""YAML configuration loader.

Loads all YAML config files from the config/ directory at the project
root and merges them into a single dict keyed by filename stem.
Provides a cached accessor for repeated access without re-reading.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env file for local development (no-op if not present)
load_dotenv()

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

_CONFIG_FILES = [
    "workstreams",
    "phases",
    "scoring",
    "personas",
    "pipeline",
    "prompts",
]

_cached_config: dict[str, Any] | None = None


def load_config(config_dir: str | None = None) -> dict[str, Any]:
    """Load all YAML config files from the config directory.

    Args:
        config_dir: Optional override for the config directory path.
            Defaults to the project-root config/ directory.

    Returns:
        Dict keyed by config file stem (e.g. "workstreams", "scoring").

    Raises:
        FileNotFoundError: If config_dir does not exist or a required
            config file is missing.
    """
    base = Path(config_dir) if config_dir else _CONFIG_DIR
    if not base.is_dir():
        msg = f"Config directory not found: {base}"
        raise FileNotFoundError(msg)

    config: dict[str, Any] = {}
    for name in _CONFIG_FILES:
        path = base / f"{name}.yml"
        if not path.exists():
            msg = f"Required config file not found: {path}"
            raise FileNotFoundError(msg)
        with path.open() as f:
            config[name] = yaml.safe_load(f)

    _apply_env_overrides(config)
    return config


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """Override config values from environment variables.

    Supports NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD for Docker deployments
    where the Neo4j hostname differs from localhost.

    Args:
        config: Mutable config dict to update in place.
    """
    pipeline = config.get("pipeline", {})
    neo4j = pipeline.get("neo4j", {})
    if uri := os.environ.get("NEO4J_URI"):
        neo4j["uri"] = uri
    if user := os.environ.get("NEO4J_USER"):
        neo4j["user"] = user
    if password := os.environ.get("NEO4J_PASSWORD"):
        neo4j["password"] = password
    postgres = pipeline.get("postgres", {})
    if dsn := os.environ.get("POSTGRES_DSN"):
        postgres["dsn"] = dsn


def get_config() -> dict[str, Any]:
    """Return the cached config, loading on first call.

    Returns:
        The merged configuration dict.
    """
    global _cached_config  # noqa: PLW0603
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config
