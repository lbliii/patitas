"""Shared token stream via ContextVar.

Eliminates re-tokenization by sharing tokens across sub-parsers.
Each parser gets a cursor into the shared stream.

Architecture:
- TokenStream: Holds all tokens for a document (stored in ContextVar)
- TokenCursor: Lightweight view into stream with position tracking
- Sub-parsers create cursors, not new streams

Performance:
- Zero re-tokenization for nested content
- O(1) cursor creation vs O(n) tokenization
- Memory: Single token list vs copies

Thread Safety:
- ContextVar ensures thread-local token streams
- Multiple threads can parse different documents safely
- Cursors are not shared across threads
"""

from contextvars import ContextVar, Token as ContextVarToken
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from patitas.tokens import Token as PatitasToken, TokenType


class TokenStream:
    """Shared token stream for a document.
    
    Stored in ContextVar for thread-local access.
    Sub-parsers create cursors instead of re-tokenizing.
    """
    
    __slots__ = ("tokens", "length", "_type_cache")
    
    def __init__(self, tokens: list[PatitasToken]) -> None:
        self.tokens = tokens
        self.length = len(tokens)
        # Cache token type sets for pattern matching
        self._type_cache: frozenset[TokenType] | None = None
    
    @property
    def types(self) -> frozenset[TokenType]:
        """Get unique token types (cached)."""
        if self._type_cache is None:
            from patitas.tokens import TokenType
            self._type_cache = frozenset(
                tok.type for tok in self.tokens 
                if tok.type != TokenType.EOF
            )
        return self._type_cache
    
    def cursor(self, start: int = 0) -> TokenCursor:
        """Create a cursor into this stream."""
        return TokenCursor(self, start)
    
    def slice_cursor(self, start: int, end: int) -> TokenCursor:
        """Create a cursor for a slice of the stream."""
        return TokenCursor(self, start, end)


class TokenCursor:
    """Lightweight cursor into a TokenStream.
    
    Provides iterator interface without copying tokens.
    Used by sub-parsers to process nested content.
    """
    
    __slots__ = ("stream", "pos", "end", "_current")
    
    def __init__(
        self, 
        stream: TokenStream, 
        start: int = 0,
        end: int | None = None,
    ) -> None:
        self.stream = stream
        self.pos = start
        self.end = end if end is not None else stream.length
        self._current: PatitasToken | None = (
            stream.tokens[start] if start < self.end else None
        )
    
    @property
    def current(self) -> PatitasToken | None:
        """Current token (cached for performance)."""
        return self._current
    
    def at_end(self) -> bool:
        """Check if cursor is at end of range."""
        return self.pos >= self.end
    
    def advance(self) -> PatitasToken | None:
        """Move to next token, return previous."""
        prev = self._current
        self.pos += 1
        self._current = (
            self.stream.tokens[self.pos] 
            if self.pos < self.end 
            else None
        )
        return prev
    
    def peek(self, offset: int = 0) -> PatitasToken | None:
        """Look ahead without advancing."""
        target = self.pos + offset
        if 0 <= target < self.end:
            return self.stream.tokens[target]
        return None
    
    def __iter__(self) -> Iterator[PatitasToken]:
        """Iterate over remaining tokens."""
        while self.pos < self.end:
            yield self.stream.tokens[self.pos]
            self.pos += 1
        self._current = None
    
    def fork(self) -> TokenCursor:
        """Create a new cursor at current position."""
        return TokenCursor(self.stream, self.pos, self.end)
    
    def remaining(self) -> int:
        """Number of tokens remaining."""
        return max(0, self.end - self.pos)


# ContextVar for thread-local token stream
_token_stream: ContextVar[TokenStream | None] = ContextVar(
    "patitas_token_stream", 
    default=None
)


def set_token_stream(stream: TokenStream) -> None:
    """Set the current thread's token stream."""
    _token_stream.set(stream)


def get_token_stream() -> TokenStream | None:
    """Get the current thread's token stream."""
    return _token_stream.get()


def clear_token_stream() -> None:
    """Clear the current thread's token stream."""
    _token_stream.set(None)


class TokenStreamContext:
    """Context manager for token stream lifecycle.
    
    Usage:
        with TokenStreamContext(tokens) as stream:
            cursor = stream.cursor()
            # parse with cursor
    """
    
    __slots__ = ("stream", "_token")
    
    stream: TokenStream
    _token: ContextVarToken[TokenStream | None] | None
    
    def __init__(self, tokens: list[PatitasToken]) -> None:
        self.stream = TokenStream(tokens)
        self._token = None
    
    def __enter__(self) -> TokenStream:
        self._token = _token_stream.set(self.stream)
        return self.stream
    
    def __exit__(self, *args: object) -> None:
        if self._token is not None:
            _token_stream.reset(self._token)
