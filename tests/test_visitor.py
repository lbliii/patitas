"""Tests for the AST visitor and transform utilities."""

import dataclasses

from patitas.location import SourceLocation
from patitas.nodes import (
    BlockQuote,
    CodeSpan,
    Document,
    Emphasis,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    LineBreak,
    Link,
    List,
    ListItem,
    Math,
    MathBlock,
    Paragraph,
    Role,
    SoftBreak,
    Strikethrough,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    ThematicBreak,
)
from patitas.visitor import BaseVisitor, transform

LOC = SourceLocation(lineno=1, col_offset=0)


def _doc(*blocks) -> Document:  # type: ignore[no-untyped-def]
    return Document(location=LOC, children=tuple(blocks))


def _para(*inlines) -> Paragraph:  # type: ignore[no-untyped-def]
    return Paragraph(location=LOC, children=tuple(inlines))


def _heading(level: int, *inlines) -> Heading:  # type: ignore[no-untyped-def]
    return Heading(location=LOC, level=level, children=tuple(inlines))  # type: ignore[arg-type]


def _text(content: str) -> Text:
    return Text(location=LOC, content=content)


# =============================================================================
# Visitor dispatch tests
# =============================================================================


class NodeCollector(BaseVisitor[None]):
    """Collects all visited node type names."""

    def __init__(self) -> None:
        self.visited: list[str] = []

    def visit_default(self, node) -> None:  # type: ignore[override]
        self.visited.append(type(node).__name__)


class TestVisitorDispatch:
    """Tests that every node type dispatches to its visit_* method."""

    def test_visits_document(self) -> None:
        doc = _doc(_para(_text("hello")))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Document" in collector.visited

    def test_visits_heading(self) -> None:
        doc = _doc(_heading(1, _text("title")))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Heading" in collector.visited
        assert "Text" in collector.visited

    def test_visits_paragraph_and_children(self) -> None:
        doc = _doc(_para(_text("a"), _text("b")))
        collector = NodeCollector()
        collector.visit(doc)
        assert collector.visited.count("Text") == 2

    def test_visits_emphasis(self) -> None:
        doc = _doc(_para(Emphasis(location=LOC, children=(_text("em"),))))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Emphasis" in collector.visited

    def test_visits_strong(self) -> None:
        doc = _doc(_para(Strong(location=LOC, children=(_text("bold"),))))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Strong" in collector.visited

    def test_visits_link(self) -> None:
        link = Link(location=LOC, url="https://example.com", title=None, children=(_text("click"),))
        doc = _doc(_para(link))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Link" in collector.visited

    def test_visits_image(self) -> None:
        img = Image(location=LOC, url="img.png", alt="photo")
        doc = _doc(_para(img))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Image" in collector.visited

    def test_visits_code_span(self) -> None:
        doc = _doc(_para(CodeSpan(location=LOC, code="x")))
        collector = NodeCollector()
        collector.visit(doc)
        assert "CodeSpan" in collector.visited

    def test_visits_line_break(self) -> None:
        doc = _doc(_para(LineBreak(location=LOC)))
        collector = NodeCollector()
        collector.visit(doc)
        assert "LineBreak" in collector.visited

    def test_visits_soft_break(self) -> None:
        doc = _doc(_para(SoftBreak(location=LOC)))
        collector = NodeCollector()
        collector.visit(doc)
        assert "SoftBreak" in collector.visited

    def test_visits_html_inline(self) -> None:
        doc = _doc(_para(HtmlInline(location=LOC, html="<br>")))
        collector = NodeCollector()
        collector.visit(doc)
        assert "HtmlInline" in collector.visited

    def test_visits_role(self) -> None:
        doc = _doc(_para(Role(location=LOC, name="ref", content="target")))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Role" in collector.visited

    def test_visits_strikethrough(self) -> None:
        doc = _doc(_para(Strikethrough(location=LOC, children=(_text("del"),))))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Strikethrough" in collector.visited

    def test_visits_math_inline(self) -> None:
        doc = _doc(_para(Math(location=LOC, content="x^2")))
        collector = NodeCollector()
        collector.visit(doc)
        assert "Math" in collector.visited

    def test_visits_footnote_ref(self) -> None:
        doc = _doc(_para(FootnoteRef(location=LOC, identifier="1")))
        collector = NodeCollector()
        collector.visit(doc)
        assert "FootnoteRef" in collector.visited

    def test_visits_fenced_code(self) -> None:
        code = FencedCode(location=LOC, source_start=0, source_end=10, info="python")
        doc = _doc(code)
        collector = NodeCollector()
        collector.visit(doc)
        assert "FencedCode" in collector.visited

    def test_visits_indented_code(self) -> None:
        doc = _doc(IndentedCode(location=LOC, code="x = 1"))
        collector = NodeCollector()
        collector.visit(doc)
        assert "IndentedCode" in collector.visited

    def test_visits_block_quote(self) -> None:
        doc = _doc(BlockQuote(location=LOC, children=(_para(_text("quoted")),)))
        collector = NodeCollector()
        collector.visit(doc)
        assert "BlockQuote" in collector.visited
        assert "Paragraph" in collector.visited

    def test_visits_list_and_items(self) -> None:
        item = ListItem(location=LOC, children=(_para(_text("item")),))
        lst = List(location=LOC, items=(item,))
        doc = _doc(lst)
        collector = NodeCollector()
        collector.visit(doc)
        assert "List" in collector.visited
        assert "ListItem" in collector.visited

    def test_visits_thematic_break(self) -> None:
        doc = _doc(ThematicBreak(location=LOC))
        collector = NodeCollector()
        collector.visit(doc)
        assert "ThematicBreak" in collector.visited

    def test_visits_html_block(self) -> None:
        doc = _doc(HtmlBlock(location=LOC, html="<div>hi</div>"))
        collector = NodeCollector()
        collector.visit(doc)
        assert "HtmlBlock" in collector.visited

    def test_visits_math_block(self) -> None:
        doc = _doc(MathBlock(location=LOC, content="E = mc^2"))
        collector = NodeCollector()
        collector.visit(doc)
        assert "MathBlock" in collector.visited

    def test_visits_footnote_def(self) -> None:
        fndef = FootnoteDef(location=LOC, identifier="1", children=(_para(_text("note")),))
        doc = _doc(fndef)
        collector = NodeCollector()
        collector.visit(doc)
        assert "FootnoteDef" in collector.visited

    def test_visits_table(self) -> None:
        cell = TableCell(location=LOC, children=(_text("A"),))
        row = TableRow(location=LOC, cells=(cell,), is_header=True)
        table = Table(location=LOC, head=(row,), body=(), alignments=(None,))
        doc = _doc(table)
        collector = NodeCollector()
        collector.visit(doc)
        assert "Table" in collector.visited
        assert "TableRow" in collector.visited
        assert "TableCell" in collector.visited


# =============================================================================
# Specific visitor override tests
# =============================================================================


class HeadingCollector(BaseVisitor[None]):
    def __init__(self) -> None:
        self.headings: list[Heading] = []

    def visit_heading(self, node: Heading) -> None:
        self.headings.append(node)


class TestSpecificVisitors:
    def test_heading_collector(self) -> None:
        doc = _doc(
            _heading(1, _text("Introduction")),
            _para(_text("body")),
            _heading(2, _text("Details")),
        )
        collector = HeadingCollector()
        collector.visit(doc)
        assert len(collector.headings) == 2
        assert collector.headings[0].level == 1
        assert collector.headings[1].level == 2

    def test_empty_document(self) -> None:
        doc = _doc()
        collector = HeadingCollector()
        collector.visit(doc)
        assert collector.headings == []


# =============================================================================
# Transform tests
# =============================================================================


class TestTransform:
    def test_identity_transform(self) -> None:
        doc = _doc(_para(_text("hello")))
        result = transform(doc, lambda node: node)
        assert result == doc

    def test_shift_heading_levels(self) -> None:
        doc = _doc(_heading(1, _text("Title")), _heading(2, _text("Sub")))

        def shift(node):  # type: ignore[no-untyped-def]
            if isinstance(node, Heading):
                return dataclasses.replace(node, level=min(node.level + 1, 6))
            return node

        result = transform(doc, shift)
        assert result.children[0].level == 2  # type: ignore[union-attr]
        assert result.children[1].level == 3  # type: ignore[union-attr]
        # Original unchanged
        assert doc.children[0].level == 1  # type: ignore[union-attr]

    def test_replace_text_content(self) -> None:
        doc = _doc(_para(_text("old")))

        def upper(node):  # type: ignore[no-untyped-def]
            if isinstance(node, Text):
                return dataclasses.replace(node, content=node.content.upper())
            return node

        result = transform(doc, upper)
        para = result.children[0]
        assert isinstance(para, Paragraph)
        assert isinstance(para.children[0], Text)
        assert para.children[0].content == "OLD"

    def test_transform_preserves_frozen(self) -> None:
        doc = _doc(_para(_text("hello")))
        result = transform(doc, lambda node: node)
        assert dataclasses.is_dataclass(result)

    def test_transform_nested_structure(self) -> None:
        doc = _doc(
            BlockQuote(
                location=LOC,
                children=(_para(_text("quoted")),),
            )
        )

        def upper(node):  # type: ignore[no-untyped-def]
            if isinstance(node, Text):
                return dataclasses.replace(node, content=node.content.upper())
            return node

        result = transform(doc, upper)
        bq = result.children[0]
        assert isinstance(bq, BlockQuote)
        para = bq.children[0]
        assert isinstance(para, Paragraph)
        assert para.children[0].content == "QUOTED"  # type: ignore[union-attr]

    def test_transform_list_items(self) -> None:
        item = ListItem(location=LOC, children=(_para(_text("item")),))
        lst = List(location=LOC, items=(item,))
        doc = _doc(lst)

        def upper(node):  # type: ignore[no-untyped-def]
            if isinstance(node, Text):
                return dataclasses.replace(node, content=node.content.upper())
            return node

        result = transform(doc, upper)
        new_list = result.children[0]
        assert isinstance(new_list, List)
        new_item = new_list.items[0]
        para = new_item.children[0]
        assert isinstance(para, Paragraph)
        assert para.children[0].content == "ITEM"  # type: ignore[union-attr]

    def test_transform_table(self) -> None:
        cell = TableCell(location=LOC, children=(_text("data"),))
        row = TableRow(location=LOC, cells=(cell,))
        table = Table(location=LOC, head=(), body=(row,), alignments=(None,))
        doc = _doc(table)

        def upper(node):  # type: ignore[no-untyped-def]
            if isinstance(node, Text):
                return dataclasses.replace(node, content=node.content.upper())
            return node

        result = transform(doc, upper)
        new_table = result.children[0]
        assert isinstance(new_table, Table)
        new_cell = new_table.body[0].cells[0]
        assert new_cell.children[0].content == "DATA"  # type: ignore[union-attr]
