"""Patitas ParseAccumulator — opt-in profiling for Markdown parsing.

This module provides accumulated metrics during parsing:
- Total parse time
- Source length
- Node count in resulting AST

Zero overhead when disabled (get_parse_accumulator() returns None).

Example:
    from patitas import parse
    from patitas.profiling import profiled_parse

    # Normal parse (no overhead)
    doc = parse("# Hello")

    # Profiled parse (opt-in)
    with profiled_parse() as metrics:
        doc = parse("# Hello **World**")

    print(metrics.summary())
    # {"total_ms": 1.2, "source_length": 18, "node_count": 4}

"""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any


@dataclass
class ParseAccumulator:
    """Accumulated metrics during Markdown parsing.

    Opt-in profiling for debugging slow parsing.
    Zero overhead when disabled (get_parse_accumulator() returns None).

    Attributes:
        start_time: Parse start timestamp.
        source_length: Length of source being parsed.
        node_count: Number of AST nodes produced.
        parse_calls: Number of parse() calls recorded.

    """

    start_time: float = field(default_factory=perf_counter)
    source_length: int = 0
    node_count: int = 0
    parse_calls: int = 0

    def record_parse(self, source_length: int, node_count: int) -> None:
        """Record a parse call.

        Args:
            source_length: Length of the source string parsed.
            node_count: Number of AST nodes in the result.

        """
        self.parse_calls += 1
        self.source_length += source_length
        self.node_count += node_count

    @property
    def total_duration_ms(self) -> float:
        """Total profiling duration in milliseconds."""
        return (perf_counter() - self.start_time) * 1000

    def summary(self) -> dict[str, Any]:
        """Get summary of parse metrics.

        Returns:
            Dict with total_ms, source_length, node_count, parse_calls.

        """
        return {
            "total_ms": round(self.total_duration_ms, 2),
            "source_length": self.source_length,
            "node_count": self.node_count,
            "parse_calls": self.parse_calls,
        }


# Module-level ContextVar
_accumulator: ContextVar[ParseAccumulator | None] = ContextVar(
    "parse_accumulator",
    default=None,
)


def get_parse_accumulator() -> ParseAccumulator | None:
    """Get current accumulator (None if profiling disabled).

    Returns:
        Current ParseAccumulator or None if not in profiled context.

    """
    return _accumulator.get()


@contextmanager
def profiled_parse() -> Iterator[ParseAccumulator]:
    """Context manager for profiled parsing.

    Creates a ParseAccumulator and makes it available via
    get_parse_accumulator() for the duration of the with block.

    Yields:
        ParseAccumulator that will be populated during parse calls.

    Example:
        with profiled_parse() as metrics:
            doc = parse(source)
        print(metrics.summary())

    """
    acc = ParseAccumulator()
    token: Token[ParseAccumulator | None] = _accumulator.set(acc)
    try:
        yield acc
    finally:
        _accumulator.reset(token)
