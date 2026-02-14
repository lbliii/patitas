"""Tests for patitas.context — content-aware context mapping."""

from patitas.context import CONTENT_CONTEXT_MAP, FALLBACK_CONTEXT_PATHS, context_paths_for
from patitas.location import SourceLocation
from patitas.nodes import (
    BlockQuote,
    Document,
    FencedCode,
    FootnoteDef,
    Heading,
    HtmlBlock,
    IndentedCode,
    List,
    MathBlock,
    Paragraph,
    Table,
    Text,
    ThematicBreak,
)

_LOC = SourceLocation(lineno=1, col_offset=0)


class TestContextPathsFor:
    def test_heading_affects_toc_and_body(self) -> None:
        node = Heading(location=_LOC, level=1, children=())
        paths = context_paths_for(node)
        assert "page.toc" in paths
        assert "page.headings" in paths
        assert "page.body" in paths

    def test_paragraph_affects_body(self) -> None:
        node = Paragraph(location=_LOC, children=())
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_fenced_code_affects_body(self) -> None:
        node = FencedCode(location=_LOC, source_start=0, source_end=0)
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_indented_code_affects_body(self) -> None:
        node = IndentedCode(location=_LOC, code="x = 1")
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_list_affects_body(self) -> None:
        node = List(location=_LOC, items=())
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_block_quote_affects_body(self) -> None:
        node = BlockQuote(location=_LOC, children=())
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_table_affects_body(self) -> None:
        node = Table(location=_LOC, head=(), body=(), alignments=())
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_thematic_break_affects_body(self) -> None:
        node = ThematicBreak(location=_LOC)
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_math_block_affects_body(self) -> None:
        node = MathBlock(location=_LOC, content="E=mc^2")
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_html_block_affects_body(self) -> None:
        node = HtmlBlock(location=_LOC, html="<div></div>")
        assert context_paths_for(node) == frozenset({"page.body"})

    def test_footnote_def_affects_body_and_footnotes(self) -> None:
        node = FootnoteDef(location=_LOC, identifier="1", children=())
        paths = context_paths_for(node)
        assert "page.body" in paths
        assert "page.footnotes" in paths

    def test_unknown_node_returns_fallback(self) -> None:
        # Text is an inline node not in the block-level map
        node = Text(location=_LOC, content="hello")
        assert context_paths_for(node) == FALLBACK_CONTEXT_PATHS

    def test_document_returns_fallback(self) -> None:
        # Document itself is not in the map (it's the root container)
        node = Document(location=_LOC, children=())
        assert context_paths_for(node) == FALLBACK_CONTEXT_PATHS


class TestMapCompleteness:
    def test_all_mapped_types_are_strings(self) -> None:
        for key in CONTENT_CONTEXT_MAP:
            assert isinstance(key, str)

    def test_all_mapped_values_are_frozensets(self) -> None:
        for value in CONTENT_CONTEXT_MAP.values():
            assert isinstance(value, frozenset)

    def test_fallback_is_conservative(self) -> None:
        # Fallback should include common paths so nothing is missed
        assert "page.body" in FALLBACK_CONTEXT_PATHS
        assert "page.toc" in FALLBACK_CONTEXT_PATHS
