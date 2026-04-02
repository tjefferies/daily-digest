"""YAML configuration loader for Daily Digest Tool.

Provides centralized access to all configuration values extracted
from YAML files in the config/ directory.
"""

from digest.config.loader import get_config, load_config

__all__ = ["get_config", "load_config"]
