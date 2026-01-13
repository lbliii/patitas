"""Tests for HtmlRenderer."""

from __future__ import annotations


class TestHtmlRenderer:
    """Tests for the HTML renderer."""

    def test_render_heading(self) -> None:
        """Test heading rendering with auto-generated ID."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, Heading, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(Text(location=loc, content="Hello World"),),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert '<h1 id="hello-world">' in html
        assert "Hello World" in html
        assert "</h1>" in html

    def test_render_paragraph(self) -> None:
        """Test paragraph rendering."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, Paragraph, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(Text(location=loc, content="Hello World"),),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert "<p>Hello World</p>" in html

    def test_render_emphasis(self) -> None:
        """Test emphasis rendering."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, Emphasis, Paragraph, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(
                        Text(location=loc, content="Hello "),
                        Emphasis(
                            location=loc,
                            children=(Text(location=loc, content="World"),),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert "<em>World</em>" in html

    def test_render_strong(self) -> None:
        """Test strong rendering."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, Paragraph, Strong, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(
                        Strong(
                            location=loc,
                            children=(Text(location=loc, content="Bold"),),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert "<strong>Bold</strong>" in html

    def test_render_link(self) -> None:
        """Test link rendering."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, Link, Paragraph, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(
                        Link(
                            location=loc,
                            url="https://example.com",
                            title="Example",
                            children=(Text(location=loc, content="Click here"),),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert 'href="https://example.com"' in html
        assert 'title="Example"' in html
        assert "Click here</a>" in html

    def test_render_code_block(self) -> None:
        """Test fenced code block rendering."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, FencedCode
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        source = "print('hello')"
        doc = Document(
            location=loc,
            children=(
                FencedCode(
                    location=loc,
                    source_start=0,
                    source_end=len(source),
                    info="python",
                    content_override=source,
                ),
            ),
        )

        renderer = HtmlRenderer(source=source)
        html = renderer.render(doc)

        assert 'class="language-python"' in html
        assert "print('hello')" in html  # Single quotes not escaped per CommonMark

    def test_render_list(self) -> None:
        """Test list rendering."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, List, ListItem, Paragraph, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                List(
                    location=loc,
                    ordered=False,
                    items=(
                        ListItem(
                            location=loc,
                            children=(
                                Paragraph(
                                    location=loc,
                                    children=(Text(location=loc, content="Item 1"),),
                                ),
                            ),
                        ),
                        ListItem(
                            location=loc,
                            children=(
                                Paragraph(
                                    location=loc,
                                    children=(Text(location=loc, content="Item 2"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert "<ul>" in html
        assert "<li>Item 1</li>" in html
        assert "<li>Item 2</li>" in html
        assert "</ul>" in html

    def test_get_headings(self) -> None:
        """Test TOC data collection."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, Heading, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(Text(location=loc, content="First"),),
                ),
                Heading(
                    location=loc,
                    level=2,
                    children=(Text(location=loc, content="Second"),),
                ),
            ),
        )

        renderer = HtmlRenderer()
        renderer.render(doc)

        headings = renderer.get_headings()
        assert len(headings) == 2
        assert headings[0].level == 1
        assert headings[0].text == "First"
        assert headings[0].slug == "first"
        assert headings[1].level == 2
        assert headings[1].text == "Second"

    def test_html_escape(self) -> None:
        """Test HTML escaping in text."""
        from patitas.location import SourceLocation
        from patitas.nodes import Document, Paragraph, Text
        from patitas.renderers.html import HtmlRenderer

        loc = SourceLocation(1, 1)
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(Text(location=loc, content="<script>alert('xss')</script>"),),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html
