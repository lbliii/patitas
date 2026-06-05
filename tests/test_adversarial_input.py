"""Adversarial / pathological input hardening tests.

The parser markets itself as "safe for untrusted input". These tests pin the
behavior on inputs designed to exhaust the interpreter stack or CPU.

Fixed (this change): deeply nested block containers (block quotes, lists,
directives) now raise a catchable ``ParseError`` via ``max_nesting_depth``
instead of crashing with an uncaught ``RecursionError``.

Fixed (issue #25): three further adversarial vectors that previously crashed are
now bounded:
  - single-line ``>``*N recursion in the *lexer* (now an iterative loop; the
    parser depth guard fires with a catchable ParseError),
  - render-time recursion on deeply nested *inline* emphasis (inline nesting is
    now bounded by ``max_nesting_depth``),
  - the O(n^2) inline bracket scan (now amortized O(n)).

Heavier security/perf bounds for these vectors live in tests/test_security_perf.py
(marked ``slow``).
"""

import time

import pytest

from patitas import Markdown
from patitas.errors import ParseError
from patitas.lexer import Lexer


@pytest.fixture
def md() -> Markdown:
    return Markdown()


class TestDeepBlockNestingIsGraceful:
    """Deeply nested block containers raise ParseError, never RecursionError."""

    def test_deep_blockquote(self, md: Markdown) -> None:
        # 150 levels: above the default depth guard (100), below the lexer's
        # own single-line recursion ceiling, so the parser guard fires.
        with pytest.raises(ParseError, match="nesting depth"):
            md(">" * 150 + " x")

    @pytest.mark.parametrize("indent", [" ", "  ", "    "])
    def test_deep_nested_lists(self, md: Markdown, indent: str) -> None:
        src = "".join(indent * i + "- x\n" for i in range(500))
        with pytest.raises(ParseError):
            md(src)

    def test_deep_blockquote_inside_directive(self, md: Markdown) -> None:
        with pytest.raises(ParseError):
            md(":::{note}\n" + ">" * 150 + " x\n:::")

    def test_deep_nesting_raises_parse_error_not_recursion(self, md: Markdown) -> None:
        # A RecursionError must never reach the caller for these inputs.
        for payload in (">" * 150 + " x", "".join("  " * i + "- a\n" for i in range(400))):
            try:
                md(payload)
            except ParseError:
                pass  # expected
            except RecursionError:  # pragma: no cover
                pytest.fail("RecursionError escaped the parser")


class TestLegitimateNestingStillWorks:
    """The guard must not reject realistic documents."""

    def test_shallow_blockquote(self, md: Markdown) -> None:
        assert md(">" * 20 + " x")

    def test_shallow_nested_list(self, md: Markdown) -> None:
        assert md("".join("  " * i + "- x\n" for i in range(12)))

    def test_realistic_document(self, md: Markdown) -> None:
        out = md("# Title\n\n- a\n  - b\n    - c\n\n> quote\n\npara")
        assert "<h1" in out and "<ul>" in out and "<blockquote>" in out


class TestMaxNestingDepthIsConfigurable:
    def test_lower_limit_triggers_earlier(self) -> None:
        md = Markdown(max_nesting_depth=5)
        with pytest.raises(ParseError):
            md(">" * 10 + " x")

    def test_within_lower_limit_parses(self) -> None:
        md = Markdown(max_nesting_depth=5)
        assert md(">" * 3 + " x")

    def test_raising_the_limit_allows_deeper(self) -> None:
        md = Markdown(max_nesting_depth=400)
        assert md(">" * 200 + " x")


class TestPreviouslyOpenHardeningGaps:
    """Adversarial vectors that previously crashed; now fixed (issue #25)."""

    def test_single_line_blockquote_markers_do_not_crash(self, md: Markdown) -> None:
        # ``>`` * N on a single line used to recurse in the *lexer* and raise an
        # uncaught RecursionError before the parser's depth guard could run. The
        # lexer is now iterative, so this input cleanly exceeds max_nesting_depth
        # and raises a catchable ParseError (NOT a RecursionError).
        with pytest.raises(ParseError, match="nesting depth"):
            md(">" * 2000 + " x")

    def test_single_line_blockquote_markers_lex_without_recursion(self) -> None:
        # The Vector 3 fix is in the *lexer*: classifying ``>`` * N on a single
        # line is now an iterative loop, not tail recursion, so it no longer
        # raises RecursionError no matter how many markers there are. (Full
        # parse+render at an artificially high max_nesting_depth would still hit
        # the parser's own recursive sub-parser -- a separate concern -- so this
        # asserts specifically that *lexing* is recursion-free.)
        try:
            tokens = list(Lexer(">" * 5000 + " x").tokenize())
        except RecursionError:  # pragma: no cover
            pytest.fail("RecursionError escaped from the lexer on deep single-line quote")
        markers = [t for t in tokens if t.type.name == "BLOCK_QUOTE_MARKER"]
        assert len(markers) == 5000

    def test_deeply_nested_emphasis_does_not_crash(self, md: Markdown) -> None:
        # Thousands of ``*`` build deeply nested Emphasis/Strong nodes. The inline
        # renderer used to recurse and raise RecursionError. The fix bounds inline
        # nesting via max_nesting_depth, so this either renders or raises a
        # catchable ParseError -- but never a RecursionError.
        try:
            md("*" * 2000 + "x" + "*" * 2000)
        except ParseError:
            pass  # acceptable: nesting exceeded max_nesting_depth
        except RecursionError:  # pragma: no cover
            pytest.fail("RecursionError escaped on deeply nested emphasis")

    def test_unmatched_brackets_are_linear(self, md: Markdown) -> None:
        # Previously O(n^2) (~4x time per 2x input). The closing-bracket search is
        # now amortized O(n), so 20000 unmatched brackets parse well under 0.5s.
        start = time.perf_counter()
        md("[" * 20000)
        assert time.perf_counter() - start < 0.5
