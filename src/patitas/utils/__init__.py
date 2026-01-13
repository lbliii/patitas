"""Utility modules for Patitas.

Provides:
- text: slugify and text processing
- hashing: hash_str for content fingerprinting
- logger: get_logger for logging
"""

from __future__ import annotations

from patitas.utils.hashing import hash_str
from patitas.utils.logger import get_logger
from patitas.utils.text import slugify

__all__ = [
    "slugify",
    "hash_str",
    "get_logger",
]
