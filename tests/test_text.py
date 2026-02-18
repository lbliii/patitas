"""Tests for extract_text()."""

from patitas import parse
from patitas.location import SourceLocation
from patitas.nodes import (
    BlockQuote,
    CodeSpan,
    Document,
    Emphasis,
    FencedCode,
    Heading,
    Image,
    IndentedCode,
    Link,
    List,
    ListItem,
    Math,
    MathBlock,
    Paragraph,
    Strong,
    Text,
)
from patitas.text import extract_text

LOC = SourceLocation(lineno=1, col_offset=0)


def _text(s: str) -> Text:
    return Text(location=LOC, content=s)


class TestExtractTextInline:
    """extract_text on inline nodes."""

    def test_text(self) -> None:
        node = _text("hello")
        assert extract_text(node) == "hello"

    def test_code_span(self) -> None:
        node = CodeSpan(location=LOC, code="x = 1")
        assert extract_text(node) == "x = 1"

    def test_math(self) -> None:
        node = Math(location=LOC, content="E = mc^2")
        assert extract_text(node) == "E = mc^2"

    def test_image(self) -> None:
        node = Image(location=LOC, url="x.png", alt="description")
        assert extract_text(node) == "description"

    def test_emphasis(self) -> None:
        node = Emphasis(location=LOC, children=(_text("em"),))
        assert extract_text(node) == "em"

    def test_strong(self) -> None:
        node = Emphasis(location=LOC, children=(_text("bold"),))
        assert extract_text(node) == "bold"

    def test_link(self) -> None:
        node = Link(
            location=LOC,
            url="https://x.com",
            title=None,
            children=(_text("click"),),
        )
        assert extract_text(node) == "click"

    def test_nested_inlines(self) -> None:
        node = Emphasis(
            location=LOC,
            children=(_text("a "), Strong(location=LOC, children=(_text("b"),)), _text(" c")),
        )
        assert extract_text(node) == "a b c"


class TestExtractTextBlock:
    """extract_text on block nodes."""

    def test_paragraph(self) -> None:
        node = Paragraph(location=LOC, children=(_text("hello"), _text(" world")))
        assert extract_text(node) == "hello world"

    def test_heading(self) -> None:
        node = Heading(location=LOC, level=1, children=(_text("Title"),))
        assert extract_text(node) == "Title"

    def test_indented_code(self) -> None:
        node = IndentedCode(location=LOC, code="x = 1")
        assert extract_text(node) == "x = 1"

    def test_math_block(self) -> None:
        node = MathBlock(location=LOC, content="E = mc^2")
        assert extract_text(node) == "E = mc^2"


class TestExtractTextDocument:
    """extract_text on full documents."""

    def test_simple_doc(self) -> None:
        doc = parse("# Hello\n\nParagraph with **bold**.")
        assert extract_text(doc) == "Hello Paragraph with bold."

    def test_empty_document(self) -> None:
        doc = Document(location=LOC, children=())
        assert extract_text(doc) == ""
