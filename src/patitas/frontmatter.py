"""
YAML frontmatter parsing for Markdown and other content formats.

Provides parse_frontmatter and extract_body with graceful error handling.
parse_frontmatter returns (metadata, body); parse_notebook returns (content, metadata).
"""

from __future__ import annotations

import contextlib
from typing import Any

import yaml

# Metadata fields that must be numeric (float).
# yaml.safe_load() preserves YAML types, so `weight: "10"` stays str while
# `weight: 10` becomes int. Normalising here prevents mixed-type comparison
# errors downstream (e.g. during sort-by-weight in SSGs).
_NUMERIC_FIELDS: frozenset[str] = frozenset({"weight", "order", "priority"})


def _find_delimiter_line(content: str) -> tuple[str, str] | None:
    """Find closing --- delimiter on its own line. Returns (frontmatter_str, body) or None."""
    if not content.startswith("---"):
        return None

    first_nl = content.find("\n")
    if first_nl == -1:
        return None

    pos = first_nl + 1
    while pos < len(content):
        next_nl = content.find("\n", pos)
        if next_nl == -1:
            line = content[pos:].strip()
            if line == "---":
                return content[first_nl + 1 : pos].strip(), content[pos + 3 :].strip()
            return None

        line = content[pos:next_nl].strip()
        if line == "---":
            frontmatter_str = content[first_nl + 1 : pos].strip()
            body = content[next_nl + 1 :].strip()
            return frontmatter_str, body

        pos = next_nl + 1

    return None


def _normalize_metadata(raw: dict[str, Any]) -> dict[str, Any]:
    """Coerce known numeric frontmatter fields to float.

    Called immediately after yaml.safe_load() so every downstream consumer
    (cascade, snapshots, sorts, templates) sees consistent types.
    """
    for key in _NUMERIC_FIELDS:
        if key in raw and raw[key] is not None:
            with contextlib.suppress(ValueError, TypeError):
                raw[key] = float(raw[key])
    return raw


def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from content. Returns (metadata, body).

    Returns (metadata, body) — complementary to parse_notebook which returns
    (markdown_content, metadata). Delimiters must be --- on their own line.

    Behavior:
    - Delimiters: --- at start, --- at end of block (line-boundary only)
    - No leading ---: return ({}, content)
    - Unclosed ---: return ({}, content) (treat as no frontmatter)
    - Valid YAML: parse with yaml.safe_load, normalize numeric fields, return (metadata, body)
    - YAML error: return ({}, body) where body = content with frontmatter block stripped

    Args:
        content: Raw file content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    split = _find_delimiter_line(content)
    if split is None:
        return {}, content

    frontmatter_str, body = split

    try:
        parsed = yaml.safe_load(frontmatter_str) or {}
        if not isinstance(parsed, dict):
            return {}, body
        return _normalize_metadata(parsed), body

    except yaml.YAMLError:
        return {}, body


def extract_body(content: str) -> str:
    """Strip --- delimited block from start. No YAML parsing.

    Uses line-boundary delimiter detection (--- on its own line), so values
    like title: \"a---b\" inside frontmatter do not truncate the body.

    Use when parse_frontmatter fails (e.g. broken YAML) but you still want
    the body content.

    Args:
        content: Full file content

    Returns:
        Content without frontmatter section
    """
    split = _find_delimiter_line(content)
    if split is not None:
        _frontmatter_str, body = split
        return body
    if content.startswith("---"):
        first_nl = content.find("\n")
        if first_nl != -1:
            return content[first_nl + 1 :].strip()
    return content.strip()
