"""
YAML frontmatter parsing for Markdown and other content formats.

Provides parse_frontmatter and extract_body with graceful error handling.
Same conceptual shape as parse_notebook for consistency across the ecosystem.
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

    Same shape as parse_notebook for consistency.

    Behavior:
    - Delimiters: --- at start, --- at end of block
    - No leading ---: return ({}, content)
    - Unclosed ---: return ({}, content) (treat as no frontmatter)
    - Valid YAML: parse with yaml.safe_load, normalize numeric fields, return (metadata, body)
    - YAML error: return ({}, body) where body = content with frontmatter block stripped

    Args:
        content: Raw file content with optional frontmatter

    Returns:
        Tuple of (frontmatter dict, body content)
    """
    if not content.startswith("---"):
        return {}, content

    try:
        end_idx = content.find("---", 3)
        if end_idx == -1:
            return {}, content

        frontmatter_str = content[3:end_idx].strip()
        body = content[end_idx + 3 :].strip()

        parsed = yaml.safe_load(frontmatter_str) or {}
        if not isinstance(parsed, dict):
            return {}, body
        return _normalize_metadata(parsed), body

    except yaml.YAMLError:
        return {}, extract_body(content)
    except Exception:
        return {}, extract_body(content)


def extract_body(content: str) -> str:
    """Strip --- delimited block from start. No YAML parsing.

    Use when parse_frontmatter fails (e.g. broken YAML) but you still want
    the body content.

    Args:
        content: Full file content

    Returns:
        Content without frontmatter section
    """
    if not content.startswith("---"):
        return content.strip()

    parts = content.split("---", 2)

    if len(parts) >= 3:
        return parts[2].strip()
    if len(parts) == 2:
        return parts[1].strip()
    return content.strip()
