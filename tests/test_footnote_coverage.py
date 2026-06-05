"""Coverage-focused tests for footnote-definition parsing
(``patitas.parsing.blocks.footnote``).

Drives the footnote parser through the PUBLIC ``Markdown(plugins=["footnotes"])``
path, covering: inline content after the colon, an empty definition (no
children), and the continuation-line branch where the body lives on following
lines rather than after the colon.
"""

from patitas import Markdown


def _md() -> Markdown:
    return Markdown(plugins=["footnotes"])


class TestFootnoteDefinitions:
    def test_inline_content_after_colon(self) -> None:
        out = _md()("Ref[^1]\n\n[^1]: the footnote body\n")
        # Reference renders as a superscript anchor.
        assert 'href="#fn-1"' in out
        # Definition body renders inside the footnotes section.
        assert "the footnote body" in out
        assert 'class="footnotes"' in out

    def test_continuation_lines_form_paragraph(self) -> None:
        # Empty content after the colon -> body collected from following lines.
        out = _md()("Ref[^a]\n\n[^a]:\nFirst line of the note.\nSecond line.\n")
        assert "First line of the note." in out
        assert "Second line." in out
        assert 'id="fn-a"' in out

    def test_empty_definition_has_no_body(self) -> None:
        out = _md()("Ref[^b]\n\n[^b]:\n")
        # Reference still present; the definition has no paragraph children.
        assert 'href="#fn-b"' in out
        assert 'id="fn-b"' in out

    def test_inline_markup_in_footnote_body(self) -> None:
        out = _md()("Ref[^c]\n\n[^c]: body with **bold** text\n")
        assert "<strong>bold</strong>" in out

    def test_multiple_footnotes_are_numbered(self) -> None:
        out = _md()("First[^one] and second[^two].\n\n[^one]: note one\n[^two]: note two\n")
        assert "note one" in out
        assert "note two" in out
        assert 'href="#fn-one"' in out
        assert 'href="#fn-two"' in out

    def test_continuation_with_blank_line_yields_two_paragraphs(self) -> None:
        out = _md()("Ref[^a]\n\n[^a]:\nFirst para line.\n\nSecond para after blank.\n")
        # Blank line inside the continuation splits into two <p> elements.
        assert out.count("<p>") >= 3  # the ref paragraph + two footnote paragraphs
        assert "First para line." in out
        assert "Second para after blank." in out

    def test_continuation_stops_at_non_paragraph_block(self) -> None:
        out = _md()("Ref[^b]\n\n[^b]:\nbody line\n# not a continuation\n")
        # The heading is NOT absorbed into the footnote; it renders separately.
        assert "<h1" in out
        assert "not a continuation" in out
        assert "body line" in out
