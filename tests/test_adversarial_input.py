"""Adversarial / pathological input hardening tests.

The parser markets itself as "safe for untrusted input". These tests pin the
behavior on inputs designed to exhaust the interpreter stack or CPU.

Fixed (this change): deeply nested block containers (block quotes, lists,
directives) now raise a catchable ``ParseError`` via ``max_nesting_depth``
instead of crashing with an uncaught ``RecursionError``.

Still open (tracked in the "adversarial input hardening" issue; marked xfail so
they flip to passing once fixed):
  - single-line ``>``*N recursion in the *lexer* (before the parser guard runs),
  - render-time recursion on deeply nested *inline* emphasis,
  - the O(n^2) inline bracket scan.
"""

import time

import pytest

from patitas import Markdown
from patitas.errors import ParseError


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


class TestKnownOpenHardeningGaps:
    """Documented, not-yet-fixed adversarial vectors (tracked separately)."""

    @pytest.mark.xfail(
        reason="single-line >*N recurses in the lexer before the parser guard; "
        "tracked in adversarial-input hardening issue",
        raises=RecursionError,
        strict=True,
    )
    def test_single_line_blockquote_markers_do_not_crash(self, md: Markdown) -> None:
        md(">" * 2000 + " x")

    @pytest.mark.xfail(
        reason="render-time recursion on deeply nested inline emphasis; "
        "tracked in adversarial-input hardening issue",
        raises=RecursionError,
        strict=True,
    )
    def test_deeply_nested_emphasis_does_not_crash(self, md: Markdown) -> None:
        md("*" * 2000 + "x" + "*" * 2000)

    @pytest.mark.xfail(
        reason="O(n^2) inline bracket scan (_find_closing_bracket); "
        "tracked in adversarial-input hardening issue",
        strict=True,
    )
    def test_unmatched_brackets_are_linear(self, md: Markdown) -> None:
        # Quadratic today: ~4x time per 2x input. Assert a generous linear-ish
        # bound so this passes only once the scan is fixed.
        start = time.perf_counter()
        md("[" * 20000)
        assert time.perf_counter() - start < 0.5
