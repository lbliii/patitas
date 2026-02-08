"""Parser dispatch based on token pattern analysis.

Pre-classifies documents by token pattern to select optimal parsing strategy.
CommonMark defines only 57 unique token patterns - we can optimize for each!

Complexity Levels:
- ULTRA_SIMPLE (47.5%): Pure inline (PARAGRAPH_LINE, BLANK_LINE only)
- SIMPLE (26.2%): No containers (headings, code blocks, HTML)
- MODERATE (10.0%): Single container type, shallow nesting
- COMPLEX (16.3%): Multiple containers, deep nesting

This pre-classification enables 3-10x speedups for simple documents.
"""

from enum import IntEnum
from typing import TYPE_CHECKING

from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.tokens import Token


class ComplexityLevel(IntEnum):
    """Document complexity classification."""

    ULTRA_SIMPLE = 0  # Pure inline - no block decisions
    SIMPLE = 1  # Leaf blocks only - no containers
    MODERATE = 2  # Single container type
    COMPLEX = 3  # Full parser needed


# Token types that indicate container structures
CONTAINER_TYPES = frozenset(
    {
        TokenType.LIST_ITEM_MARKER,
        TokenType.BLOCK_QUOTE_MARKER,
    }
)

# Token types that indicate potential nesting complexity
NESTING_TYPES = frozenset(
    {
        TokenType.INDENTED_CODE,  # Could be nested list content
    }
)

# Simple leaf block types (no nesting)
LEAF_BLOCK_TYPES = frozenset(
    {
        TokenType.ATX_HEADING,
        TokenType.SETEXT_HEADING_UNDERLINE,
        TokenType.FENCED_CODE_START,
        TokenType.FENCED_CODE_CONTENT,
        TokenType.FENCED_CODE_END,
        TokenType.HTML_BLOCK,
        TokenType.THEMATIC_BREAK,
        TokenType.LINK_REFERENCE_DEF,
    }
)

# Ultra-simple types (pure inline)
ULTRA_SIMPLE_TYPES = frozenset(
    {
        TokenType.PARAGRAPH_LINE,
        TokenType.BLANK_LINE,
        TokenType.EOF,
    }
)


def classify_complexity(tokens: list[Token]) -> ComplexityLevel:
    """Classify document complexity based on token pattern.

    O(n) scan of tokens to determine optimal parsing strategy.
    This classification cost is amortized by faster parsing.

    Args:
        tokens: List of tokens from lexer

    Returns:
        ComplexityLevel indicating optimal parsing strategy
    """
    has_container = False
    has_nesting = False
    container_types_seen: set[TokenType] = set()
    max_indent = 0

    for tok in tokens:
        tok_type = tok.type

        # Check for container types
        if tok_type in CONTAINER_TYPES:
            has_container = True
            container_types_seen.add(tok_type)

        # Check for nesting indicators
        if tok_type in NESTING_TYPES:
            has_nesting = True

        # Track indentation
        if tok.line_indent > max_indent:
            max_indent = tok.line_indent

        # Early exit: if we've seen multiple container types or deep nesting
        if len(container_types_seen) > 1 or max_indent > 4:
            return ComplexityLevel.COMPLEX

    # Classify based on findings
    if not has_container and not has_nesting:
        # Check if truly ultra-simple (only PARAGRAPH_LINE, BLANK_LINE, EOF)
        if all(tok.type in ULTRA_SIMPLE_TYPES or tok.type in LEAF_BLOCK_TYPES for tok in tokens):
            # Ultra-simple if no leaf blocks
            if all(tok.type in ULTRA_SIMPLE_TYPES for tok in tokens):
                return ComplexityLevel.ULTRA_SIMPLE
            return ComplexityLevel.SIMPLE
        return ComplexityLevel.SIMPLE

    if len(container_types_seen) == 1 and max_indent <= 4:
        return ComplexityLevel.MODERATE

    return ComplexityLevel.COMPLEX


def get_token_pattern(tokens: list[Token]) -> tuple[TokenType, ...]:
    """Get unique token type pattern for pattern matching.

    Returns a sorted tuple of unique token types, which can be used
    as a key for pattern-specific optimizations.

    Args:
        tokens: List of tokens from lexer

    Returns:
        Sorted tuple of unique TokenTypes
    """
    return tuple(sorted({tok.type for tok in tokens if tok.type != TokenType.EOF}))
