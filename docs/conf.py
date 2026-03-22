"""Sphinx configuration for ghud documentation."""

project = "ghud"
copyright = "2026, Teague Sterling"
author = "Teague Sterling"
release = "0.1.0"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
]

templates_path = ["_templates"]
exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"

myst_enable_extensions = [
    "colon_fence",
]
