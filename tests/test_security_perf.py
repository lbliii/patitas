"""Heavier security / performance bounds for adversarial input (issue #25).

These exercise the same three vectors as ``TestPreviouslyOpenHardeningGaps`` in
``tests/test_adversarial_input.py`` but at larger sizes that would have crashed or
hung before the fix. They are marked ``slow`` so they stay out of the default fast
path; CI's primary step runs them. Every bound here must be *fast* and *bounded* --
the whole point is that the fixes make these inputs cheap, not that they take a long
time to fail.

Vectors:
  1. O(n^2) inline bracket scan -> now amortized O(n).
  2. Render-time recursion on deeply nested inline emphasis -> now bounded by
     ``max_nesting_depth`` (catchable ParseError, never RecursionError).
  3. Single-line ``>`` * N lexer recursion -> lexer is now iterative; the parser
     depth guard raises a catchable ParseError quickly.
"""

import time

import pytest

from patitas import Markdown
from patitas.errors import ParseError
from patitas.lexer import Lexer

pytestmark = pytest.mark.slow


@pytest.fixture
def md() -> Markdown:
    return Markdown()


def test_unmatched_brackets_100k_is_fast(md: Markdown) -> None:
    """100000 unmatched '[' parse in well under 100ms (was quadratic)."""
    start = time.perf_counter()
    md("[" * 100_000)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.1, f"100k '[' took {elapsed * 1000:.1f}ms (expected < 100ms)"


def test_bracket_scan_scales_linearly(md: Markdown) -> None:
    """Doubling the input must not quadruple the time (linear, not quadratic)."""

    def timed(n: int) -> float:
        # Best-of-3 to reduce noise; we only care about the growth ratio.
        best = float("inf")
        for _ in range(3):
            start = time.perf_counter()
            md("[" * n)
            best = min(best, time.perf_counter() - start)
        return best

    t1 = timed(20_000)
    t2 = timed(40_000)
    # A quadratic scan would give a ratio near 4x; allow generous headroom for
    # noise but stay well below quadratic.
    assert t2 < t1 * 3.0, f"non-linear bracket scan: t(20k)={t1:.4f}s t(40k)={t2:.4f}s"


def test_deeply_nested_emphasis_5000_no_recursion_error(md: Markdown) -> None:
    """5000+5000 '*' must not raise RecursionError; ParseError is acceptable."""
    try:
        md("*" * 5000 + "x" + "*" * 5000)
    except ParseError:
        pass  # bounded by max_nesting_depth -- expected
    except RecursionError:  # pragma: no cover
        pytest.fail("RecursionError escaped on deeply nested emphasis")


def test_single_line_blockquote_100k_raises_parse_error_quickly(md: Markdown) -> None:
    """100000 single-line '>' must raise ParseError fast, never RecursionError."""
    start = time.perf_counter()
    with pytest.raises(ParseError, match="nesting depth"):
        md(">" * 100_000 + " x")
    elapsed = time.perf_counter() - start
    # The lexer is now iterative and the depth guard fires up front, so this is
    # dominated by linear lexing of the markers -- not the former ~minute-long
    # quadratic re-lexing.
    assert elapsed < 3.0, f"deep single-line quote took {elapsed:.2f}s (expected < 3s)"


def test_single_line_blockquote_lexes_without_recursion() -> None:
    """Lexing a very deep single-line quote must not recurse per '>'.

    The Vector 3 fix turned the per-marker tail recursion in the lexer's block
    quote classifier into a loop, so even 100000 markers on one line lex without
    a RecursionError. (Full parse+render at such depth is governed separately by
    the parser's recursive sub-parser and max_nesting_depth guard.)
    """
    start = time.perf_counter()
    try:
        tokens = list(Lexer(">" * 100_000 + " x").tokenize())
    except RecursionError:  # pragma: no cover
        pytest.fail("RecursionError escaped from the lexer on deep single-line quote")
    elapsed = time.perf_counter() - start
    markers = [t for t in tokens if t.type.name == "BLOCK_QUOTE_MARKER"]
    assert len(markers) == 100_000
    # Lexing must be linear, not the former O(n^2) re-expansion of the tail.
    assert elapsed < 3.0, f"lexing 100k '>' took {elapsed:.2f}s (expected < 3s)"
