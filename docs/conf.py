"""Sphinx configuration for Daily Digest Tool documentation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

project = "Daily Digest Tool"
copyright = "2026, Travis Jefferies"  # noqa: A001
author = "Travis Jefferies"
release = "0.1.0"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = ["_static"]

html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#3F51B5",
        "color-brand-content": "#3F51B5",
    },
    "dark_css_variables": {
        "color-brand-primary": "#7986CB",
        "color-brand-content": "#7986CB",
    },
    "sidebar_hide_name": False,
    "navigation_with_keys": True,
}

# Napoleon settings (Google style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Autodoc settings
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "member-order": "bysource",
}
autodoc_typehints = "description"

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}

# Suppress noisy warnings from third-party docstrings
suppress_warnings = [
    "ref.ref",       # Unknown cross-reference targets from SQLAlchemy
    "ref.doc",       # Missing document references
]

# Nitpick: ignore unresolvable type references from third-party libs
nitpick_ignore = [
    ("py:class", "JsonValue"),
    ("py:class", "SQLCoreOperations"),
    ("py:class", "Mapper"),
    ("py:class", "TableClause"),
    ("py:class", "AsyncLLMClient"),
    ("py:class", "Embedder"),
    ("py:class", "ScoredAtom"),
    ("py:class", "FilterResult"),
    ("py:class", "SlackMessage"),
    ("py:class", "ThreadBundle"),
    ("py:class", "ContextWindow"),
    ("py:class", "Atom"),
    ("py:class", "Persona"),
    ("py:class", "DigestSection"),
    ("py:class", "BatchExtractionRunner"),
    ("py:class", "PipelineResult"),
]

# Don't fail on unknown roles from SQLAlchemy docstrings
rst_prolog = """
.. role:: paramref
"""
