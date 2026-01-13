"""Directive parsing mixin for Patitas parser.

STUB: This is a placeholder for directive parsing functionality.
The full implementation requires Bengal-specific dependencies that will
be added in Phase 5 of the extraction (tiered directives).

For now, directives are parsed at the lexer level but not expanded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from patitas.nodes import Block, Directive
    from patitas.directives.options import DirectiveOptions


class DirectiveParsingMixin:
    """Mixin providing directive parsing.
    
    STUB: Directive expansion is not yet implemented in the extracted package.
    Directives are tokenized but returned as raw Directive nodes without
    content processing or registered handler invocation.
    
    Full directive support requires:
    - patitas[directives] for portable directives (admonition, dropdown, tabs)
    - patitas[bengal] for Bengal-specific directives (cards, code-tabs, etc.)
    """

    def _parse_directive_block(self) -> Block | None:
        """Parse a directive block.
        
        STUB: Returns None until full directive support is implemented.
        The lexer still produces directive tokens, which will be skipped
        or treated as raw content.
        """
        return None
