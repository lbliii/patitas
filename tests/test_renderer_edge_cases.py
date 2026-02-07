"""Edge case tests for HtmlRenderer.

These tests cover scenarios that revealed bugs during code review:
- Thread safety with shared renderer instances
- Standalone ListItem rendering
- Duplicate footnote references
- Complex tight list structures
- Exception handling in directive/role handlers
- Image alt text in heading slugs
"""

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

import pytest

from patitas.location import SourceLocation
from patitas.nodes import (
    BlockQuote,
    CodeSpan,
    Document,
    Emphasis,
    FootnoteDef,
    FootnoteRef,
    Heading,
    Image,
    Link,
    List,
    ListItem,
    Paragraph,
    Role,
    Strong,
    Text,
)
from patitas.renderers.html import HtmlRenderer, RenderContext

if TYPE_CHECKING:
    pass


# Shared test fixtures
@pytest.fixture
def loc() -> SourceLocation:
    """Default source location for test nodes."""
    return SourceLocation(1, 1)


class TestThreadSafety:
    """Tests for concurrent rendering with shared HtmlRenderer instances."""

    def test_shared_renderer_concurrent_renders(self, loc: SourceLocation) -> None:
        """Multiple threads can safely share one renderer instance."""
        doc1 = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(Text(location=loc, content="Document One"),),
                ),
            ),
        )
        doc2 = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(Text(location=loc, content="Document Two"),),
                ),
            ),
        )

        shared_renderer = HtmlRenderer()
        results: dict[str, str] = {}
        errors: list[Exception] = []

        def render(name: str, doc: Document) -> None:
            try:
                html = shared_renderer.render(doc)
                results[name] = html
            except Exception as e:
                errors.append(e)

        # Run concurrent renders
        threads = [
            threading.Thread(target=render, args=("doc1", doc1)),
            threading.Thread(target=render, args=("doc2", doc2)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent rendering raised: {errors}"
        assert "Document One" in results["doc1"]
        assert "Document Two" in results["doc2"]

    def test_heading_slugs_isolated_between_renders(self, loc: SourceLocation) -> None:
        """Heading slug deduplication doesn't leak between concurrent renders."""
        # Both docs have the same heading text
        doc1 = Document(
            location=loc,
            children=(
                Heading(
                    location=loc, level=1, children=(Text(location=loc, content="Title"),)
                ),
            ),
        )
        doc2 = Document(
            location=loc,
            children=(
                Heading(
                    location=loc, level=1, children=(Text(location=loc, content="Title"),)
                ),
            ),
        )

        shared_renderer = HtmlRenderer()

        # Run many concurrent renders to stress test
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for i in range(20):
                doc = doc1 if i % 2 == 0 else doc2
                futures.append(executor.submit(shared_renderer.render, doc))

            for future in as_completed(futures):
                html = future.result()
                # Each render should get "title" (not "title-1" from leaked state)
                assert 'id="title"' in html, "Slug deduplication leaked between renders"

    def test_footnote_state_isolated(self, loc: SourceLocation) -> None:
        """Footnote collection doesn't leak between concurrent renders."""
        doc_with_footnote = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(
                        Text(location=loc, content="Text"),
                        FootnoteRef(location=loc, identifier="fn1"),
                    ),
                ),
                FootnoteDef(
                    location=loc,
                    identifier="fn1",
                    children=(
                        Paragraph(
                            location=loc, children=(Text(location=loc, content="Note"),)
                        ),
                    ),
                ),
            ),
        )
        doc_without_footnote = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc, children=(Text(location=loc, content="Plain text"),)
                ),
            ),
        )

        shared_renderer = HtmlRenderer()

        def render_and_check(doc: Document, should_have_footnotes: bool) -> None:
            html = shared_renderer.render(doc)
            has_footnotes = '<section class="footnotes">' in html
            assert has_footnotes == should_have_footnotes

        # Run concurrent renders with mixed documents
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [
                executor.submit(render_and_check, doc_with_footnote, True),
                executor.submit(render_and_check, doc_without_footnote, False),
                executor.submit(render_and_check, doc_with_footnote, True),
                executor.submit(render_and_check, doc_without_footnote, False),
            ]
            for future in as_completed(futures):
                future.result()  # Raises if assertion failed


class TestStandaloneListItem:
    """Tests for ListItem rendered outside of a List container."""

    def test_standalone_list_item_renders(self, loc: SourceLocation) -> None:
        """Standalone ListItem renders without TypeError."""
        doc = Document(
            location=loc,
            children=(
                ListItem(
                    location=loc,
                    children=(
                        Paragraph(
                            location=loc, children=(Text(location=loc, content="Item"),)
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert "<li>" in html
        assert "Item" in html
        assert "</li>" in html

    def test_standalone_list_item_with_checkbox(self, loc: SourceLocation) -> None:
        """Standalone task list item renders checkbox correctly."""
        doc = Document(
            location=loc,
            children=(
                ListItem(
                    location=loc,
                    checked=True,
                    children=(
                        Paragraph(
                            location=loc, children=(Text(location=loc, content="Done"),)
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert '<input type="checkbox" disabled checked />' in html


class TestFootnoteEdgeCases:
    """Tests for footnote rendering edge cases."""

    def test_duplicate_footnote_references_single_definition(
        self, loc: SourceLocation
    ) -> None:
        """Same footnote referenced multiple times produces valid HTML."""
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(
                        Text(location=loc, content="First"),
                        FootnoteRef(location=loc, identifier="note"),
                        Text(location=loc, content=" and second"),
                        FootnoteRef(location=loc, identifier="note"),
                        Text(location=loc, content=" and third"),
                        FootnoteRef(location=loc, identifier="note"),
                    ),
                ),
                FootnoteDef(
                    location=loc,
                    identifier="note",
                    children=(
                        Paragraph(
                            location=loc,
                            children=(Text(location=loc, content="The footnote"),),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        # Should have exactly ONE footnote definition in the section
        assert html.count('id="fn-note"') == 1, "Duplicate footnote definitions"

        # Should have three unique reference IDs
        assert 'id="fnref-note-1"' in html
        assert 'id="fnref-note-2"' in html
        assert 'id="fnref-note-3"' in html

    def test_footnote_ref_without_definition(self, loc: SourceLocation) -> None:
        """Footnote reference without definition still renders (no crash)."""
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(
                        Text(location=loc, content="Text"),
                        FootnoteRef(location=loc, identifier="missing"),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        # Reference should render
        assert 'href="#fn-missing"' in html
        # But footnotes section should be empty (no li elements)
        assert '<section class="footnotes">' in html
        assert "<li" not in html.split('<section class="footnotes">')[1]

    def test_multiple_different_footnotes(self, loc: SourceLocation) -> None:
        """Multiple distinct footnotes render in reference order."""
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(
                        FootnoteRef(location=loc, identifier="second"),  # Referenced first
                        FootnoteRef(location=loc, identifier="first"),  # Referenced second
                    ),
                ),
                FootnoteDef(
                    location=loc,
                    identifier="first",
                    children=(
                        Paragraph(location=loc, children=(Text(location=loc, content="A"),)),
                    ),
                ),
                FootnoteDef(
                    location=loc,
                    identifier="second",
                    children=(
                        Paragraph(location=loc, children=(Text(location=loc, content="B"),)),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        # Footnotes rendered in order of first reference
        footnotes_section = html.split('<section class="footnotes">')[1]
        second_pos = footnotes_section.find('id="fn-second"')
        first_pos = footnotes_section.find('id="fn-first"')
        assert second_pos < first_pos, "Footnotes should be in reference order"


class TestTightListComplexStructures:
    """Tests for tight lists with complex block structures."""

    def test_tight_list_heading_then_paragraph(self, loc: SourceLocation) -> None:
        """Tight list item with heading followed by paragraph."""
        doc = Document(
            location=loc,
            children=(
                List(
                    location=loc,
                    tight=True,
                    items=(
                        ListItem(
                            location=loc,
                            children=(
                                Heading(
                                    location=loc,
                                    level=3,
                                    children=(Text(location=loc, content="Header"),),
                                ),
                                Paragraph(
                                    location=loc,
                                    children=(Text(location=loc, content="Description"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        # Paragraph should be rendered as inline text (no <p> tags in tight list)
        assert "<h3" in html
        assert "Description" in html
        assert html.count("<p>") == 0, "Tight list shouldn't wrap paragraph in <p>"

    def test_tight_list_blockquote_then_paragraph(self, loc: SourceLocation) -> None:
        """Tight list item with blockquote followed by paragraph."""
        doc = Document(
            location=loc,
            children=(
                List(
                    location=loc,
                    tight=True,
                    items=(
                        ListItem(
                            location=loc,
                            children=(
                                BlockQuote(
                                    location=loc,
                                    children=(
                                        Paragraph(
                                            location=loc,
                                            children=(Text(location=loc, content="Quote"),),
                                        ),
                                    ),
                                ),
                                Paragraph(
                                    location=loc,
                                    children=(Text(location=loc, content="After quote"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        assert "<blockquote>" in html
        assert "After quote" in html


class TestHeadingSlugGeneration:
    """Tests for heading ID/slug generation."""

    def test_image_alt_included_in_slug(self, loc: SourceLocation) -> None:
        """Image alt text is included in heading slug."""
        doc = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(
                        Text(location=loc, content="Hello "),
                        Image(location=loc, url="world.png", alt="world"),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)
        headings = renderer.get_headings()

        assert headings[0].slug == "hello-world"
        assert headings[0].text == "Hello world"

    def test_code_span_included_in_slug(self, loc: SourceLocation) -> None:
        """Code span content is included in heading slug."""
        doc = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(
                        Text(location=loc, content="The "),
                        CodeSpan(location=loc, code="main"),
                        Text(location=loc, content=" function"),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)
        headings = renderer.get_headings()

        assert headings[0].slug == "the-main-function"

    def test_nested_emphasis_in_slug(self, loc: SourceLocation) -> None:
        """Nested emphasis text is included in heading slug."""
        doc = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(
                        Strong(
                            location=loc,
                            children=(
                                Emphasis(
                                    location=loc,
                                    children=(Text(location=loc, content="Important"),),
                                ),
                            ),
                        ),
                        Text(location=loc, content=" section"),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        renderer.render(doc)
        headings = renderer.get_headings()

        assert headings[0].slug == "important-section"

    def test_link_text_in_slug(self, loc: SourceLocation) -> None:
        """Link text (not URL) is included in heading slug."""
        doc = Document(
            location=loc,
            children=(
                Heading(
                    location=loc,
                    level=1,
                    children=(
                        Text(location=loc, content="See "),
                        Link(
                            location=loc,
                            url="https://example.com/docs",
                            title=None,
                            children=(Text(location=loc, content="documentation"),),
                        ),
                    ),
                ),
            ),
        )

        renderer = HtmlRenderer()
        renderer.render(doc)
        headings = renderer.get_headings()

        assert headings[0].slug == "see-documentation"
        assert "example.com" not in headings[0].slug

    def test_duplicate_heading_slugs_deduplicated(self, loc: SourceLocation) -> None:
        """Duplicate heading text gets deduplicated slugs."""
        doc = Document(
            location=loc,
            children=(
                Heading(
                    location=loc, level=2, children=(Text(location=loc, content="Section"),)
                ),
                Heading(
                    location=loc, level=2, children=(Text(location=loc, content="Section"),)
                ),
                Heading(
                    location=loc, level=2, children=(Text(location=loc, content="Section"),)
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)
        headings = renderer.get_headings()

        assert headings[0].slug == "section"
        assert headings[1].slug == "section-1"
        assert headings[2].slug == "section-2"

        # Verify IDs are in HTML
        assert 'id="section"' in html
        assert 'id="section-1"' in html
        assert 'id="section-2"' in html


class TestRenderContext:
    """Tests for RenderContext isolation."""

    def test_render_context_is_independent(self) -> None:
        """Each RenderContext is independent."""
        ctx1 = RenderContext()
        ctx2 = RenderContext()

        ctx1.seen_slugs.add("test")
        ctx1.footnote_refs.append("fn1")

        assert "test" not in ctx2.seen_slugs
        assert "fn1" not in ctx2.footnote_refs

    def test_render_context_default_values(self) -> None:
        """RenderContext initializes with empty collections."""
        ctx = RenderContext()

        assert ctx.headings == []
        assert ctx.seen_slugs == set()
        assert ctx.footnote_defs == {}
        assert ctx.footnote_refs == []


class TestExceptionHandling:
    """Tests for graceful degradation when handlers fail."""

    def test_render_role_without_registry(self, loc: SourceLocation) -> None:
        """Role renders with default styling when no registry is configured."""
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(Role(location=loc, name="kbd", content="Ctrl+C"),),
                ),
            ),
        )

        renderer = HtmlRenderer()  # No role_registry
        html = renderer.render(doc)

        assert 'class="role role-kbd"' in html
        assert "Ctrl+C" in html

    def test_html_escape_in_role_name(self, loc: SourceLocation) -> None:
        """Role name is HTML-escaped in default rendering."""
        doc = Document(
            location=loc,
            children=(
                Paragraph(
                    location=loc,
                    children=(Role(location=loc, name='test"><script>', content="text"),),
                ),
            ),
        )

        renderer = HtmlRenderer()
        html = renderer.render(doc)

        # XSS attempt should be escaped
        assert "<script>" not in html
        assert "&lt;script&gt;" in html or "test&quot;&gt;&lt;script&gt;" in html
