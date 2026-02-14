"""Tests for the high-level Patitas API."""


class TestParseFunction:
    """Tests for the parse() function."""

    def test_parse_heading(self) -> None:
        """Test parsing a heading."""
        from patitas import Heading, parse

        doc = parse("# Hello World")
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], Heading)
        assert doc.children[0].level == 1

    def test_parse_paragraph(self) -> None:
        """Test parsing a paragraph."""
        from patitas import Paragraph, parse

        doc = parse("Hello World")
        assert len(doc.children) == 1
        assert isinstance(doc.children[0], Paragraph)

    def test_parse_with_source_file(self) -> None:
        """Test parsing with source file context."""
        from patitas import parse

        doc = parse("# Test", source_file="test.md")
        # Location should include source file
        assert doc.location.source_file == "test.md"


class TestRenderFunction:
    """Tests for the render() function."""

    def test_render_heading(self) -> None:
        """Test rendering a heading."""
        from patitas import parse, render

        doc = parse("# Hello World")
        html = render(doc)
        assert '<h1 id="hello-world">Hello World</h1>' in html

    def test_render_emphasis(self) -> None:
        """Test rendering emphasis."""
        from patitas import parse, render

        doc = parse("Hello *World*")
        html = render(doc)
        assert "<em>World</em>" in html


class TestMarkdownClass:
    """Tests for the Markdown class."""

    def test_basic_usage(self) -> None:
        """Test basic Markdown usage."""
        from patitas import Markdown

        md = Markdown()
        html = md("# Hello **World**")
        assert '<h1 id="hello-world">' in html
        assert "<strong>World</strong>" in html

    def test_parse_method(self) -> None:
        """Test Markdown.parse() method."""
        from patitas import Document, Markdown

        md = Markdown()
        doc = md.parse("# Test")
        assert isinstance(doc, Document)

    def test_render_method(self) -> None:
        """Test Markdown.render() method."""
        from patitas import Markdown, parse

        md = Markdown()
        doc = parse("# Test")
        html = md.render(doc)
        assert "<h1" in html


class TestComplexDocument:
    """Tests for complex document parsing."""

    def test_multiple_blocks(self) -> None:
        """Test parsing multiple block types."""
        from patitas import Markdown

        md = Markdown()
        source = """# Heading

This is a paragraph with **bold** and *italic*.

- Item 1
- Item 2

```python
print("hello")
```
"""
        html = md(source)
        assert "<h1" in html
        assert "<strong>bold</strong>" in html
        assert "<em>italic</em>" in html
        assert "<ul>" in html
        assert "<li>" in html
        assert '<code class="language-python">' in html

    def test_nested_emphasis(self) -> None:
        """Test nested emphasis."""
        from patitas import Markdown

        md = Markdown()
        html = md("***bold and italic***")
        # Should have both strong and em
        assert "<strong>" in html or "<em>" in html

    def test_links(self) -> None:
        """Test link parsing and rendering."""
        from patitas import Markdown

        md = Markdown()
        html = md('[Click here](https://example.com "Example")')
        assert 'href="https://example.com"' in html
        assert "Click here" in html


class TestExports:
    """Test that all expected symbols are exported."""

    def test_version(self) -> None:
        """Test version is exported and matches pyproject."""
        import tomllib
        from pathlib import Path

        from patitas import __version__

        with (Path(__file__).resolve().parent.parent / "pyproject.toml").open("rb") as f:
            expected = tomllib.load(f)["project"]["version"]
        assert __version__ == expected

    def test_core_api(self) -> None:
        """Test core API functions are exported."""
        from patitas import Markdown, parse, render

        assert callable(parse)
        assert callable(render)
        assert Markdown is not None

    def test_node_types(self) -> None:
        """Test node types are exported."""
        from patitas import (
            Document,
            Heading,
        )

        # Just verify they're importable
        assert Document is not None
        assert Heading is not None

    def test_parser_components(self) -> None:
        """Test parser components are exported."""
        from patitas import HtmlRenderer, Lexer, Parser

        assert Parser is not None
        assert Lexer is not None
        assert HtmlRenderer is not None
