"""Tests for extract_excerpt and extract_meta_description."""


from patitas import extract_excerpt, extract_meta_description, parse


class TestExtractExcerpt:
    """Tests for extract_excerpt."""

    def test_short_content(self) -> None:
        """Short content returns full text after h1."""
        doc = parse("# Title\n\nFirst paragraph. Second sentence.")
        result = extract_excerpt(doc)
        assert "First paragraph" in result
        assert "Second sentence" in result
        assert "Title" not in result

    def test_skips_leading_h1(self) -> None:
        """Leading h1 is skipped by default."""
        doc = parse("# Intro\n\nContent here.")
        result = extract_excerpt(doc)
        assert "Content here" in result
        assert "Intro" not in result

    def test_includes_headings(self) -> None:
        """Headings are included in excerpt."""
        doc = parse("# Doc\n\n## Key Features\n\nFast builds.")
        result = extract_excerpt(doc)
        assert "Key Features" in result or "Fast builds" in result

    def test_truncates_at_boundary(self) -> None:
        """Excerpt stops at block boundary within max_chars."""
        content = "# Title\n\n" + "Word " * 100
        doc = parse(content)
        result = extract_excerpt(doc, max_chars=100)
        assert len(result) <= 110  # 100 + "..."

    def test_empty_returns_empty(self) -> None:
        """Empty document returns empty string."""
        doc = parse("")
        assert extract_excerpt(doc) == ""

    def test_sequence_of_blocks(self) -> None:
        """Accepts Sequence[Block] from parse_to_ast."""
        from patitas.parser import Parser

        source = "# Title\n\nFirst paragraph."
        parser = Parser(source)
        blocks = parser.parse()
        result = extract_excerpt(blocks, source)
        assert "First paragraph" in result

    def test_excerpt_as_html_preserves_structure(self) -> None:
        """excerpt_as_html=True uses block elements (p, excerpt-heading) and preserves inline."""
        doc = parse("# Title\n\nPara with **bold** and *italic*.\n\n## Key Features\n\nMore text.")
        result = extract_excerpt(doc, excerpt_as_html=True)
        assert "<strong>bold</strong>" in result
        assert "<em>italic</em>" in result
        assert "Key Features" in result
        assert "excerpt-heading" in result
        assert "<p>" in result

    def test_excerpt_as_html_plain_text_fallback(self) -> None:
        """excerpt_as_html=False returns plain text (default)."""
        doc = parse("# Title\n\nPara with **bold**.")
        result = extract_excerpt(doc, excerpt_as_html=False)
        assert "bold" in result
        assert "<strong>" not in result

    def test_excerpt_as_html_lists_use_ul_ol_li(self) -> None:
        """excerpt_as_html=True renders lists with ul/ol and li elements."""
        doc = parse("# Title\n\n- First item\n- Second item\n\n1. Ordered one\n2. Ordered two")
        result = extract_excerpt(doc, excerpt_as_html=True)
        assert "<ul" in result or "excerpt-list" in result
        assert "<li>" in result
        assert "First item" in result
        assert "Second item" in result


class TestExtractMetaDescription:
    """Tests for extract_meta_description."""

    def test_sentence_boundary(self) -> None:
        """Meta description prefers sentence boundary when over 160 chars."""
        content = "# Title\n\n" + "Word " * 20 + "First sentence. " + "More " * 30 + "text."
        doc = parse(content)
        result = extract_meta_description(doc)
        # Should end at sentence boundary, not mid-word
        assert len(result) <= 165
        assert result.rstrip().endswith((".", "!", "?")) or "..." in result

    def test_max_160_chars(self) -> None:
        """Meta description respects 160 char limit."""
        content = "# Title\n\n" + "Word " * 50
        doc = parse(content)
        result = extract_meta_description(doc)
        assert len(result) <= 165  # 160 + "..."

    def test_short_content_full(self) -> None:
        """Short content returns full text."""
        doc = parse("# Title\n\nHi.")
        result = extract_meta_description(doc)
        assert "Hi" in result
