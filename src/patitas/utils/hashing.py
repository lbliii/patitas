"""Cryptographic hashing utilities for Patitas.

Provides standardized hashing for cache keys and content fingerprinting.

Example:
    >>> from patitas.utils.hashing import hash_str
    >>> hash_str("hello world")
    'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
    >>> hash_str("hello world", truncate=16)
    'b94d27b9934d3e08'
"""

from __future__ import annotations

import hashlib


def hash_str(
    content: str,
    truncate: int | None = None,
    algorithm: str = "sha256",
) -> str:
    """Hash string content using specified algorithm.

    Args:
        content: String content to hash
        truncate: Truncate result to N characters (None = full hash)
        algorithm: Hash algorithm ('sha256', 'md5')

    Returns:
        Hex digest of hash, optionally truncated

    Examples:
        >>> hash_str("hello")
        '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
        >>> hash_str("hello", truncate=16)
        '2cf24dba5fb0a30e'
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content.encode("utf-8"))
    digest = hasher.hexdigest()
    return digest[:truncate] if truncate else digest


def hash_bytes(
    content: bytes,
    truncate: int | None = None,
    algorithm: str = "sha256",
) -> str:
    """Hash bytes content using specified algorithm.

    Args:
        content: Bytes content to hash
        truncate: Truncate result to N characters (None = full hash)
        algorithm: Hash algorithm ('sha256', 'md5')

    Returns:
        Hex digest of hash, optionally truncated
    """
    hasher = hashlib.new(algorithm)
    hasher.update(content)
    digest = hasher.hexdigest()
    return digest[:truncate] if truncate else digest
