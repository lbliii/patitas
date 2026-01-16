"""Utility modules for Patitas.

Provides:
- text: slugify, escape_html for text processing
- hashing: hash_str, hash_bytes for content fingerprinting
- logger: get_logger for logging
"""

from __future__ import annotations

from patitas.utils.hashing import hash_bytes, hash_str
from patitas.utils.logger import get_logger
from patitas.utils.text import escape_html, slugify

__all__ = [
    "escape_html",
    "get_logger",
    "hash_bytes",
    "hash_str",
    "slugify",
]
