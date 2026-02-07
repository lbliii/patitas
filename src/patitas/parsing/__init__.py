"""Parsing subsystem for Patitas Markdown parser.

Provides mixin classes for modular parsing functionality:
- `TokenNavigationMixin`: Token stream traversal
- `InlineParsingMixin`: Inline content (emphasis, links, code spans)
- `BlockParsingMixin`: Block-level content (paragraphs, lists, code blocks)

Architecture:
The parser uses a mixin-based design for separation of concerns,
following the same pattern as Kida's parser. Each mixin handles
one aspect of the Markdown grammar.

Example:
    >>> from patitas.parsing import (
    ...     TokenNavigationMixin,
    ...     InlineParsingMixin,
    ...     BlockParsingMixin,
    ... )
    >>> class Parser(TokenNavigationMixin, InlineParsingMixin, BlockParsingMixin):
    ...     pass

Public API:
TokenNavigationMixin: Token stream navigation and lookahead
InlineParsingMixin: Combined inline parsing (emphasis, links, etc.)
BlockParsingMixin: Combined block parsing (lists, tables, etc.)

"""

from patitas.parsing.blocks import BlockParsingMixin
from patitas.parsing.inline import InlineParsingMixin
from patitas.parsing.protocols import ParserHost
from patitas.parsing.token_nav import TokenNavigationMixin

__all__ = [
    "TokenNavigationMixin",
    "InlineParsingMixin",
    "BlockParsingMixin",
    "ParserHost",
]
