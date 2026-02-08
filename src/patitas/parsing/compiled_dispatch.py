"""Compile-time dispatch for pattern-based parsing.

Generates optimized dispatch code at module load time based on
CommonMark token patterns. Uses Python 3.10+ match/case for
efficient pattern matching.

Architecture:
1. At import time: Build pattern → parser lookup table
2. At parse time: O(1) lookup based on token type signature
3. Fallback: Standard parser for unknown patterns

Performance:
- O(1) parser selection (dict lookup)
- No runtime pattern analysis
- Specialized parsers eliminate branching

Future: Could generate Cython code for even faster dispatch.
"""

from typing import TYPE_CHECKING, Callable, TypeAlias

from patitas.tokens import TokenType

if TYPE_CHECKING:
    from patitas.nodes import Block
    from patitas.tokens import Token

# Type alias for parser functions
ParserFn: TypeAlias = Callable[["list[Token]", Callable], "tuple[Block, ...]"]


class PatternDispatcher:
    """Compile-time pattern → parser dispatcher.
    
    Built once at module load, used for all parses.
    Uses frozenset of token types as pattern signature.
    """
    
    __slots__ = ("_dispatch_table", "_stats")
    
    def __init__(self) -> None:
        self._dispatch_table: dict[frozenset[TokenType], ParserFn] = {}
        self._stats = {
            "hits": 0,
            "misses": 0,
            "patterns_seen": set(),
        }
    
    def register(
        self, 
        pattern: frozenset[TokenType], 
        parser: ParserFn,
    ) -> None:
        """Register a parser for a token pattern."""
        self._dispatch_table[pattern] = parser
    
    def get_parser(self, tokens: list[Token]) -> ParserFn | None:
        """Get parser for token pattern, or None for fallback.
        
        O(1) lookup after O(n) signature computation.
        Signature computation is very cheap (just type checks).
        """
        # Compute pattern signature (exclude EOF)
        pattern = frozenset(
            tok.type for tok in tokens 
            if tok.type != TokenType.EOF
        )
        
        # Track stats for optimization tuning
        self._stats["patterns_seen"].add(pattern)
        
        parser = self._dispatch_table.get(pattern)
        if parser is not None:
            self._stats["hits"] += 1
        else:
            self._stats["misses"] += 1
        
        return parser
    
    def get_stats(self) -> dict:
        """Get dispatch statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total if total > 0 else 0
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "patterns_registered": len(self._dispatch_table),
            "patterns_seen": len(self._stats["patterns_seen"]),
        }


def build_dispatcher() -> PatternDispatcher:
    """Build the pattern dispatcher at module load time.
    
    Registers ONLY patterns where token types alone determine parsing.
    
    NOT registered (require content analysis):
    - PARAGRAPH_LINE patterns: Can contain setext underlines (===, ---), tables
    - LIST patterns: Can contain indented code, complex nesting
    - FENCED_CODE: FencedCode node uses source_start/source_end tracking
    
    These are handled by the ultra-fast path (can_use_ultra_fast) or
    the main parser's existing fast paths.
    """
    from patitas.parsing.pattern_parsers import (
        parse_atx_only,
        parse_html_only,
        parse_indented_only,
    )
    
    dispatcher = PatternDispatcher()
    
    # Pattern 3: HTML only (3.7%)
    # Safe: HTML_BLOCK tokens are unambiguous
    dispatcher.register(
        frozenset({TokenType.HTML_BLOCK}),
        parse_html_only,
    )
    
    # Pattern 9: ATX headings only (2.1%)
    # Safe: ATX_HEADING tokens are unambiguous
    dispatcher.register(
        frozenset({TokenType.ATX_HEADING}),
        parse_atx_only,
    )
    
    # Pattern 10: Indented code only (2.0%)
    # Safe: INDENTED_CODE tokens are unambiguous
    dispatcher.register(
        frozenset({TokenType.INDENTED_CODE}),
        parse_indented_only,
    )
    
    return dispatcher


# Build dispatcher at module load time
# This is the "compile-time" part - happens once per process
_DISPATCHER: PatternDispatcher | None = None


def get_dispatcher() -> PatternDispatcher:
    """Get the global pattern dispatcher (lazy initialization)."""
    global _DISPATCHER
    if _DISPATCHER is None:
        _DISPATCHER = build_dispatcher()
    return _DISPATCHER


def dispatch_parse(
    tokens: list[Token],
    parse_inline_fn: Callable,
    fallback_fn: Callable,
) -> tuple:
    """Dispatch to optimal parser based on token pattern.
    
    Args:
        tokens: Token list from lexer
        parse_inline_fn: Function to parse inline content
        fallback_fn: Standard parser for unknown patterns
        
    Returns:
        Tuple of Block nodes
    """
    dispatcher = get_dispatcher()
    parser = dispatcher.get_parser(tokens)
    
    if parser is not None:
        return parser(tokens, parse_inline_fn)
    else:
        return fallback_fn()
