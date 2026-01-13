"""ContextVar-based parse configuration for Patitas.

Provides thread-local configuration using Python's ContextVars (PEP 567).
Config is set once per Markdown instance, read by all parsers in the context.

Thread Safety:
    ContextVars are thread-local by design. Each thread has independent storage,
    so no locks are needed and race conditions are impossible.

Usage:
    # In Markdown class
    md = Markdown(plugins=["tables", "math"])
    html = md("# Hello")  # Sets config internally via ContextVar

    # Direct parser usage (advanced)
    from patitas.config import set_parse_config, reset_parse_config, ParseConfig
    
    set_parse_config(ParseConfig(tables_enabled=True))
    try:
        parser = Parser(source)
        result = parser.parse()
    finally:
        reset_parse_config()

    # Or use the context manager
    with parse_config_context(ParseConfig(tables_enabled=True)):
        parser = Parser(source)
        result = parser.parse()

"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from patitas.directives.registry import DirectiveRegistry


@dataclass(frozen=True, slots=True)
class ParseConfig:
    """Immutable parse configuration.

    Set once per Markdown instance, read by all parsers in the context.
    Frozen dataclass ensures thread-safety (immutable after creation).

    Note: source_file is intentionally excluded—it's per-call state,
    not configuration. It remains on the Parser instance.

    Attributes:
        tables_enabled: Enable GFM table parsing
        strikethrough_enabled: Enable ~~strikethrough~~ syntax
        task_lists_enabled: Enable - [ ] task list items
        footnotes_enabled: Enable [^ref] footnote references
        math_enabled: Enable $inline$ and $$block$$ math
        autolinks_enabled: Enable automatic URL linking
        directive_registry: Registry for directive handlers
        strict_contracts: Raise errors on directive contract violations
        text_transformer: Optional callback to transform plain text lines

    """

    tables_enabled: bool = False
    strikethrough_enabled: bool = False
    task_lists_enabled: bool = False
    footnotes_enabled: bool = False
    math_enabled: bool = False
    autolinks_enabled: bool = False
    directive_registry: DirectiveRegistry | None = None
    strict_contracts: bool = False
    text_transformer: Callable[[str], str] | None = None


# Module-level default config (reused, never recreated)
_DEFAULT_CONFIG: ParseConfig = ParseConfig()

# Thread-local configuration via ContextVar
_parse_config: ContextVar[ParseConfig] = ContextVar(
    "parse_config",
    default=_DEFAULT_CONFIG,
)


def get_parse_config() -> ParseConfig:
    """Get current parse configuration (thread-local).

    Returns:
        The active ParseConfig for this thread/context.

    Thread Safety:
        ContextVars are thread-local by design. Safe to call from any thread.

    """
    return _parse_config.get()


def set_parse_config(config: ParseConfig) -> None:
    """Set parse configuration for current context.

    Args:
        config: ParseConfig instance to use for this context.

    Thread Safety:
        Only affects the current thread's context. Other threads are unaffected.

    """
    _parse_config.set(config)


def reset_parse_config() -> None:
    """Reset to default configuration.

    Reuses the module-level _DEFAULT_CONFIG singleton, avoiding allocation.

    Thread Safety:
        Only affects the current thread's context. Other threads are unaffected.

    """
    _parse_config.set(_DEFAULT_CONFIG)


@contextmanager
def parse_config_context(config: ParseConfig) -> Iterator[None]:
    """Context manager for temporary config changes.

    Useful for tests and isolated parsing operations.

    Args:
        config: ParseConfig to use within the context.

    Yields:
        None

    Example:
        >>> with parse_config_context(ParseConfig(tables_enabled=True)):
        ...     parser = Parser("| a | b |")
        ...     result = parser.parse()
        ...     # tables_enabled is True here
        >>> # Automatically reset to previous config

    Thread Safety:
        Only affects the current thread's context. Properly restores previous
        config even if an exception is raised.

    """
    previous = _parse_config.get()
    _parse_config.set(config)
    try:
        yield
    finally:
        _parse_config.set(previous)


__all__ = [
    "ParseConfig",
    "get_parse_config",
    "set_parse_config",
    "reset_parse_config",
    "parse_config_context",
]
