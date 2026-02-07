"""Tests for complex scenarios involving multiple classifier mixins.

These tests verify that the different block classifiers work correctly
together when blocks are nested inside other blocks (e.g., headings
inside block quotes, lists inside block quotes, etc.).
"""

import pytest

from patitas.lexer import Lexer
from patitas.tokens import TokenType


class TestBlockQuoteNestedBlocks:
    """Test block quotes containing various other block types."""

    def test_blockquote_with_heading(self) -> None:
        """Block quote should correctly identify ATX heading inside."""
        source = "> # Heading in quote"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.ATX_HEADING in token_types

    def test_blockquote_with_list(self) -> None:
        """Block quote should correctly identify list inside."""
        source = "> - list item"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.LIST_ITEM_MARKER in token_types

    def test_blockquote_with_code_fence(self) -> None:
        """Block quote should correctly identify code fence start inside.
        
        Note: Code fence detection in block quotes is line-based. The fence
        must start at the beginning of the quoted content (after > marker).
        """
        source = "> ```python"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.FENCED_CODE_START in token_types

    def test_blockquote_with_thematic_break(self) -> None:
        """Block quote should correctly identify thematic break inside."""
        source = "> ---"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.THEMATIC_BREAK in token_types

    def test_blockquote_nested_blockquote(self) -> None:
        """Nested block quotes should be correctly identified."""
        source = "> > nested quote"
        tokens = list(Lexer(source).tokenize())

        quote_markers = [t for t in tokens if t.type == TokenType.BLOCK_QUOTE_MARKER]
        assert len(quote_markers) == 2

    def test_blockquote_with_link_reference(self) -> None:
        """Block quote should recognize link reference definitions."""
        source = "> [label]: /url"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.LINK_REFERENCE_DEF in token_types

    def test_blockquote_containing_all_block_types(self) -> None:
        """Block quote should correctly delegate to all classifiers."""
        source = """> # Heading
> 
> - list item
> 
> ```python
> 
> ---
"""
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.ATX_HEADING in token_types
        assert TokenType.LIST_ITEM_MARKER in token_types
        assert TokenType.FENCED_CODE_START in token_types
        assert TokenType.THEMATIC_BREAK in token_types


class TestListNestedBlocks:
    """Test list items containing various other block types."""

    def test_list_with_heading(self) -> None:
        """List item should correctly identify ATX heading inside."""
        source = "- # Heading in list"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.LIST_ITEM_MARKER in token_types
        assert TokenType.ATX_HEADING in token_types

    def test_list_with_blockquote(self) -> None:
        """List item should correctly identify block quote inside."""
        source = "- > quote in list"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.LIST_ITEM_MARKER in token_types
        assert TokenType.BLOCK_QUOTE_MARKER in token_types

    def test_list_with_thematic_break(self) -> None:
        """List item should correctly identify thematic break inside.
        
        Note: '- ---' on its own line is parsed as a single thematic break
        (dash followed by more dashes). To get a list item containing a
        thematic break, we need clearer separation.
        """
        source = "- ***"  # Asterisk thematic break after dash list marker
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.LIST_ITEM_MARKER in token_types
        assert TokenType.THEMATIC_BREAK in token_types

    def test_list_with_code_fence(self) -> None:
        """List item should correctly identify code fence inside.
        
        Note: Code fences need to be properly formatted - the opening
        backticks should be on their own or followed only by info string.
        """
        source = "- ```python"  # List marker followed by fence start
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.LIST_ITEM_MARKER in token_types
        assert TokenType.FENCED_CODE_START in token_types

    def test_nested_list(self) -> None:
        """Nested lists should be correctly identified."""
        source = "- - nested item"
        tokens = list(Lexer(source).tokenize())

        list_markers = [t for t in tokens if t.type == TokenType.LIST_ITEM_MARKER]
        assert len(list_markers) == 2

    def test_list_item_containing_nested_blocks(self) -> None:
        """List items should correctly classify nested block content."""
        source = """- # Heading in list
- > blockquote in list
- ```python
"""
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.LIST_ITEM_MARKER in token_types
        assert TokenType.ATX_HEADING in token_types
        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.FENCED_CODE_START in token_types


class TestDirectiveNestedBlocks:
    """Test directives containing various other block types."""

    def test_directive_with_heading(self) -> None:
        """Directive should correctly identify ATX heading inside."""
        source = ":::{note}\n# Heading\n:::"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.DIRECTIVE_OPEN in token_types
        assert TokenType.ATX_HEADING in token_types

    def test_directive_with_list(self) -> None:
        """Directive should correctly identify list inside."""
        source = ":::{note}\n- item\n:::"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.DIRECTIVE_OPEN in token_types
        assert TokenType.LIST_ITEM_MARKER in token_types

    def test_directive_with_blockquote(self) -> None:
        """Directive should correctly identify block quote inside."""
        source = ":::{note}\n> quote\n:::"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.DIRECTIVE_OPEN in token_types
        assert TokenType.BLOCK_QUOTE_MARKER in token_types

    def test_directive_with_code_fence(self) -> None:
        """Directive should correctly identify code fence inside."""
        source = ":::{note}\n```\ncode\n```\n:::"
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.DIRECTIVE_OPEN in token_types
        assert TokenType.FENCED_CODE_START in token_types

    def test_nested_directives(self) -> None:
        """Nested directives should be correctly identified."""
        source = ":::{outer}\n::::{inner}\ncontent\n::::\n:::"
        tokens = list(Lexer(source).tokenize())

        directive_opens = [t for t in tokens if t.type == TokenType.DIRECTIVE_OPEN]
        assert len(directive_opens) == 2


class TestDeeplyNestedStructures:
    """Test deeply nested combinations of blocks."""

    def test_deeply_nested_blockquotes(self) -> None:
        """Deeply nested block quotes should tokenize correctly."""
        source = "> > > > deeply nested quote"
        tokens = list(Lexer(source).tokenize())

        quote_markers = [t for t in tokens if t.type == TokenType.BLOCK_QUOTE_MARKER]
        assert len(quote_markers) == 4

    def test_deeply_nested_lists(self) -> None:
        """Deeply nested lists should tokenize correctly."""
        source = "- - - - deeply nested list"
        tokens = list(Lexer(source).tokenize())

        list_markers = [t for t in tokens if t.type == TokenType.LIST_ITEM_MARKER]
        assert len(list_markers) == 4

    def test_blockquote_in_list_in_blockquote(self) -> None:
        """Complex nesting: blockquote > list > blockquote."""
        source = "> - > nested"
        tokens = list(Lexer(source).tokenize())
        token_types = [t.type for t in tokens]

        # Should have multiple quote markers and a list marker
        assert token_types.count(TokenType.BLOCK_QUOTE_MARKER) >= 2
        assert TokenType.LIST_ITEM_MARKER in token_types

    def test_no_exceptions_on_deep_nesting(self) -> None:
        """Deep nesting should not cause stack overflow or exceptions."""
        # 20 levels of nested block quotes
        source = "> " * 20 + "content"
        # Should not raise
        tokens = list(Lexer(source).tokenize())
        assert len(tokens) > 0


class TestMixedBlockTypes:
    """Test documents with multiple different block types."""

    def test_full_document_structure(self) -> None:
        """Full document with various block types should tokenize correctly."""
        source = """# Heading 1

Paragraph text here.

> Block quote with content

- List item 1
- List item 2

```python
code block
```

---

## Heading 2

More paragraph text.
"""
        tokens = list(Lexer(source).tokenize())
        token_types = {t.type for t in tokens}

        assert TokenType.ATX_HEADING in token_types
        assert TokenType.PARAGRAPH_LINE in token_types
        assert TokenType.BLOCK_QUOTE_MARKER in token_types
        assert TokenType.LIST_ITEM_MARKER in token_types
        assert TokenType.FENCED_CODE_START in token_types
        assert TokenType.THEMATIC_BREAK in token_types
        assert TokenType.BLANK_LINE in token_types
