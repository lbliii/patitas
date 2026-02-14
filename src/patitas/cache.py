"""Content-addressed parse cache for Patitas.

Provides (content_hash, config_hash) -> Document caching to avoid re-parsing
unchanged content. Enables faster incremental builds (undo/revert, duplicate
content) and can replace path-based snapshot caches in consumers like Bengal.

Thread Safety:
    DictParseCache is not thread-safe. For parallel parsing, use a cache
    implementation with internal locking (e.g. threading.Lock around get/put).

Example:
    >>> from patitas import parse, DictParseCache
    >>> cache = DictParseCache()
    >>> doc1 = parse("# Hello", cache=cache)
    >>> doc2 = parse("# Hello", cache=cache)  # Cache hit, no re-parse
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from patitas.utils.hashing import hash_str

if TYPE_CHECKING:
    from patitas.config import ParseConfig
    from patitas.nodes import Document


class ParseCache(Protocol):
    """Protocol for content-addressed parse caches.

    Cache key is (content_hash, config_hash). Cached value is Document (AST).
    Document is immutable, safe to share across threads.
    """

    def get(self, content_hash: str, config_hash: str) -> Document | None:
        """Return cached Document if present, else None."""
        ...

    def put(self, content_hash: str, config_hash: str, doc: Document) -> None:
        """Store Document in cache."""
        ...


class DictParseCache:
    """In-memory parse cache using a dict.

    Not thread-safe. For parallel parsing, wrap with a lock or use a
    thread-safe implementation.
    """

    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data: dict[tuple[str, str], Document] = {}

    def get(self, content_hash: str, config_hash: str) -> Document | None:
        """Return cached Document if present, else None."""
        return self._data.get((content_hash, config_hash))

    def put(self, content_hash: str, config_hash: str, doc: Document) -> None:
        """Store Document in cache."""
        self._data[(content_hash, config_hash)] = doc


def hash_content(source: str) -> str:
    """Compute SHA256 hash of source for cache key.

    Args:
        source: Markdown source text

    Returns:
        Hex digest of SHA256 hash
    """
    return hash_str(source)


def hash_config(config: ParseConfig) -> str:
    """Compute hash of ParseConfig for cache key.

    When text_transformer is set, returns empty string to disable caching
    (transformer affects output in non-hashable way).

    Args:
        config: ParseConfig to hash

    Returns:
        Hex digest of config hash, or "" if cache should be bypassed
    """
    if config.text_transformer is not None:
        return ""
    parts = (
        str(config.tables_enabled),
        str(config.strikethrough_enabled),
        str(config.task_lists_enabled),
        str(config.footnotes_enabled),
        str(config.math_enabled),
        str(config.autolinks_enabled),
        str(config.strict_contracts),
        str(id(config.directive_registry)),
    )
    return hash_str("|".join(parts))


__all__ = [
    "DictParseCache",
    "ParseCache",
    "hash_config",
    "hash_content",
]
