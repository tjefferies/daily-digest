"""YAML configuration loader for EverCurrent.

Provides centralized access to all configuration values extracted
from YAML files in the config/ directory.
"""

from evercurrent.config.loader import get_config, load_config

__all__ = ["get_config", "load_config"]
