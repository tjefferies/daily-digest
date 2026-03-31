"""YAML configuration loader.

Loads all YAML config files from the config/ directory at the project
root and merges them into a single dict keyed by filename stem.
Provides a cached accessor for repeated access without re-reading.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"

_CONFIG_FILES = [
    "workstreams",
    "phases",
    "scoring",
    "personas",
    "pipeline",
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

    return config


def get_config() -> dict[str, Any]:
    """Return the cached config, loading on first call.

    Returns:
        The merged configuration dict.
    """
    global _cached_config  # noqa: PLW0603
    if _cached_config is None:
        _cached_config = load_config()
    return _cached_config
