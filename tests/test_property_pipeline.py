"""End-to-end property tests for the full parse -> render pipeline.

Part D of issue #28: several existing property tests only fuzzed the *lexer* or
asserted nothing (a bare ``parse``/``pass``). These tests drive the PUBLIC
``Markdown()`` pipeline (``parse -> render``) on generated inputs and assert real
invariants:

* rendering always returns a ``str`` and never raises (for any plugin set),
* re-rendering the parsed AST is idempotent (``render(parse(x)) ==
  render(parse(x))``),
* simple inline inputs produce balanced ``<p>`` / ``<strong>`` / ``<em>`` tags
  (no unclosed tags),
* the AST -> ``render`` round trip is stable across repeated parses.

Kept fast: small inputs, modest example counts.
"""

import re

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from patitas import Markdown, parse, render
from patitas.plugins import BUILTIN_PLUGINS

_PLUGIN_NAMES = list(BUILTIN_PLUGINS.keys())

# Markdown-ish text: a mix of plain words, structural punctuation, and newlines.
_markdownish = st.text(
    alphabet="abcXYZ 0123\n#*_`>-[]()!|~^:.",
    max_size=120,
)

_plugin_sets = st.lists(
    st.sampled_from(_PLUGIN_NAMES),
    max_size=len(_PLUGIN_NAMES),
    unique=True,
)

# Simple, safe inline content that should always yield well-formed paragraphs.
_simple_inline = st.text(
    alphabet="abc XYZ 123",
    min_size=1,
    max_size=40,
).filter(lambda s: s.strip() != "")


def _count_tags(html: str, tag: str) -> tuple[int, int]:
    opens = len(re.findall(rf"<{tag}(?:\s[^>]*)?>", html))
    closes = len(re.findall(rf"</{tag}>", html))
    return opens, closes


class TestPipelineNeverCrashes:
    @given(source=_markdownish)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_default_markdown_returns_str_and_never_raises(self, source: str) -> None:
        md = Markdown()
        out = md(source)
        assert isinstance(out, str)

    @given(source=_markdownish, plugins=_plugin_sets)
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
    def test_any_plugin_set_returns_str_and_never_raises(
        self, source: str, plugins: list[str]
    ) -> None:
        md = Markdown(plugins=plugins)
        out = md(source)
        assert isinstance(out, str)


class TestPipelineDeterminism:
    @given(source=_markdownish)
    @settings(max_examples=150, suppress_health_check=[HealthCheck.too_slow])
    def test_render_is_idempotent_across_repeated_parses(self, source: str) -> None:
        # Same input -> identical HTML every time (no hidden global state).
        first = render(parse(source), source=source)
        second = render(parse(source), source=source)
        assert first == second

    @given(source=_markdownish)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_rerendering_same_ast_is_stable(self, source: str) -> None:
        doc = parse(source)
        a = render(doc, source=source)
        b = render(doc, source=source)
        assert a == b


class TestSimpleInputsAreWellFormed:
    @given(text=_simple_inline)
    @settings(max_examples=200, suppress_health_check=[HealthCheck.too_slow])
    def test_plain_text_yields_balanced_paragraph(self, text: str) -> None:
        out = Markdown()(text)
        p_open, p_close = _count_tags(out, "p")
        assert p_open == p_close, f"unbalanced <p> in {out!r}"

    @given(word=st.text(alphabet="abcXYZ123", min_size=1, max_size=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_strong_emphasis_is_balanced(self, word: str) -> None:
        out = Markdown()(f"**{word}**")
        s_open, s_close = _count_tags(out, "strong")
        assert s_open == s_close == 1, f"unbalanced <strong> in {out!r}"
        assert word in out

    @given(word=st.text(alphabet="abcXYZ123", min_size=1, max_size=20))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_emphasis_is_balanced(self, word: str) -> None:
        out = Markdown()(f"*{word}*")
        e_open, e_close = _count_tags(out, "em")
        assert e_open == e_close == 1, f"unbalanced <em> in {out!r}"
        assert word in out

    @given(
        word=st.text(alphabet="abcXYZ123", min_size=1, max_size=20),
        level=st.integers(min_value=1, max_value=6),
    )
    @settings(max_examples=80, suppress_health_check=[HealthCheck.too_slow])
    def test_atx_heading_is_balanced(self, word: str, level: int) -> None:
        out = Markdown()(f"{'#' * level} {word}")
        h_open, h_close = _count_tags(out, f"h{level}")
        assert h_open == h_close == 1, f"unbalanced <h{level}> in {out!r}"
        assert word in out
