"""Heavier security / performance bounds for adversarial input (issue #25).

These exercise the same three vectors as ``TestPreviouslyOpenHardeningGaps`` in
``tests/test_adversarial_input.py`` but at larger sizes that would have crashed or
hung before the fix. They are marked ``slow`` so they stay out of the default fast
path; the nightly ``slow-tests`` CI job runs them. Most bounds here must be *fast*
and *bounded* -- the fixes make those inputs cheap, not slow to fail. The exception
is the bracket-scan regression below (Vector 1), which only guards a generous upper
bound on a path that is still O(n^2) by design.

Vectors:
  1. O(n^2) inline bracket scan -> the unmatched-``[`` case (no closing bracket) is
     now linear (#36); other bracket-heavy inputs remain O(n^2) but bounded and
     documented (see issue #39 and docs/security.md#known-limitations).
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


# ---------------------------------------------------------------------------
# Bracket-heavy inputs that remain super-linear (issue #39).
#
# The inline bracket scan is still O(n^2) on adversarial input (documented under
# "Known limitations" in docs/security.md; the README no longer claims strict
# O(n)). These do NOT assert a fast/linear bound -- that would be dishonest and
# fragile. They assert only that the parser *completes* within a very generous
# bound, so the inputs stay exercised and any blow-up to worse-than-quadratic
# (or exponential) behavior is caught as a regression.
# ---------------------------------------------------------------------------

# Modest size: large enough to be clearly quadratic, small enough that the
# generous bound below leaves ample headroom for noisy CI.
_PATHOLOGICAL_N = 2000

# Generous upper bound (seconds). Locally these complete in well under a second
# at this size; the bound only fails if the path degrades badly past quadratic.
_PATHOLOGICAL_BUDGET = 10.0


@pytest.mark.parametrize(
    ("label", "make_source"),
    [
        ("unmatched-open", lambda n: "[" * n + "x]"),
        ("balanced-brackets", lambda n: "[" * n + "x" + "]" * n),
        ("empty-link-open-paren", lambda n: "[](" * n),
    ],
)
def test_bracket_heavy_input_completes_within_budget(md: Markdown, label: str, make_source) -> None:
    """Bracket-heavy adversarial inputs complete within a generous bound.

    The inline bracket scan is O(n^2) here (see docs/security.md "Known
    limitations"), so this only guards against a worse-than-quadratic blow-up,
    not against quadratic time itself.
    """
    source = make_source(_PATHOLOGICAL_N)
    start = time.perf_counter()
    md(source)
    elapsed = time.perf_counter() - start
    assert elapsed < _PATHOLOGICAL_BUDGET, (
        f"{label} (n={_PATHOLOGICAL_N}) took {elapsed:.2f}s (expected < {_PATHOLOGICAL_BUDGET}s)"
    )
