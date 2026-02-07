"""Token and TokenType definitions for the Patitas lexer.

The lexer produces a stream of Token objects that the parser consumes.
Each Token has a type, value, and source location.

Thread Safety:
Token is frozen (immutable) and safe to share across threads.
TokenType is an enum (inherently immutable).

Performance Note:
Token stores raw coordinates and lazily creates SourceLocation on demand.
This avoids allocating SourceLocation objects for tokens whose location
is never accessed (most tokens during parsing).

"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from patitas.location import SourceLocation


class TokenType(Enum):
    """Token types produced by the lexer.

    Organized by category for clarity:
    - Document structure (EOF, BLANK_LINE)
    - Block elements (headings, code blocks, quotes, lists)
    - Inline elements (text, emphasis, links, images)
    - Directives and roles

    """

    # Document structure
    EOF = auto()
    BLANK_LINE = auto()

    # Block elements - headings
    ATX_HEADING = auto()  # # Heading
    SETEXT_HEADING_UNDERLINE = auto()  # === or ---

    # Block elements - code
    FENCED_CODE_START = auto()  # ``` or ~~~
    FENCED_CODE_END = auto()
    FENCED_CODE_CONTENT = auto()
    INDENTED_CODE = auto()  # 4-space indented

    # Block elements - quotes and lists
    BLOCK_QUOTE_MARKER = auto()  # >
    LIST_ITEM_MARKER = auto()  # -, *, +, 1., 1)

    # Block elements - other
    THEMATIC_BREAK = auto()  # ---, ***, ___
    HTML_BLOCK = auto()

    # Paragraph and text
    PARAGRAPH_LINE = auto()  # Regular text line
    TEXT = auto()  # Inline text content

    # Inline elements - emphasis
    EMPHASIS_MARKER = auto()  # * or _
    STRONG_MARKER = auto()  # ** or __

    # Inline elements - code
    CODE_SPAN = auto()  # `code`

    # Inline elements - links and images
    LINK_START = auto()  # [
    LINK_END = auto()  # ]
    LINK_DESTINATION = auto()  # (url "title")
    IMAGE_START = auto()  # ![
    AUTOLINK = auto()  # <url>

    # Inline elements - other
    HARD_BREAK = auto()  # \\ or two trailing spaces
    SOFT_BREAK = auto()  # Single newline in paragraph
    HTML_INLINE = auto()  # Inline HTML

    # Inline elements - escapes
    ESCAPED_CHAR = auto()  # \* \_ etc.

    # Reference definitions
    LINK_REFERENCE_DEF = auto()  # [label]: url "title"

    # Directive system (MyST-compatible)
    DIRECTIVE_OPEN = auto()  # :::
    DIRECTIVE_CLOSE = auto()  # ::: (matching)
    DIRECTIVE_NAME = auto()  # {name}
    DIRECTIVE_TITLE = auto()  # Title text after name
    DIRECTIVE_OPTION = auto()  # :key: value

    # Role system (MyST-compatible)
    ROLE = auto()  # {role}`content`

    # Plugin tokens - Tables (GFM)
    TABLE_ROW = auto()  # | cell | cell |
    TABLE_DELIMITER = auto()  # |---|---|

    # Plugin tokens - Strikethrough
    STRIKETHROUGH_MARKER = auto()  # ~~

    # Plugin tokens - Math
    MATH_INLINE = auto()  # $...$
    MATH_BLOCK_START = auto()  # $$
    MATH_BLOCK_END = auto()  # $$
    MATH_BLOCK_CONTENT = auto()

    # Plugin tokens - Footnotes
    FOOTNOTE_REF = auto()  # [^id]
    FOOTNOTE_DEF = auto()  # [^id]:

    # Zero-Copy Lexer Handoff (ZCLH)
    SUB_LEXER_TOKENS = auto()  # Delegated tokens from a sub-lexer


@dataclass(frozen=True, slots=True)
class Token:
    """A token produced by the lexer.

    Tokens are the atomic units passed from lexer to parser.
    Each token has a type, string value, and source location (lazy).

    Attributes:
        type: The token type (from TokenType enum)
        value: The raw string value from source
        _lineno: Start line number (1-indexed)
        _col: Start column offset (1-indexed)
        _start_offset: Absolute start position in source
        _end_offset: Absolute end position in source
        line_indent: Pre-computed indent level of the line (spaces, tabs expand to 4).
            Set by lexer at token creation; -1 if not computed.
        _end_lineno: End line number (for multi-line tokens)
        _end_col: End column offset
        _source_file: Optional source file path

    Performance:
        SourceLocation is created lazily on first access to `.location`.
        This avoids allocation overhead for tokens whose location is never read.

    Thread Safety:
        Frozen dataclass ensures immutability for safe sharing.
        The lazy cache uses idempotent write (safe for concurrent access).

    """

    type: TokenType
    value: str
    _lineno: int
    _col: int
    _start_offset: int
    _end_offset: int
    line_indent: int = -1  # Pre-computed by lexer; -1 = not computed
    _end_lineno: int | None = None
    _end_col: int | None = None
    _source_file: str | None = None
    # Cache field - excluded from repr and comparison
    _location_cache: SourceLocation | None = field(
        default=None, repr=False, compare=False, hash=False
    )

    @property
    def location(self) -> SourceLocation:
        """Get source location (lazily created and cached).

        Returns:
            SourceLocation object for this token.
        """
        if self._location_cache is not None:
            return self._location_cache

        # Import here to avoid circular import at module load
        from patitas.location import SourceLocation

        loc = SourceLocation(
            lineno=self._lineno,
            col_offset=self._col,
            offset=self._start_offset,
            end_offset=self._end_offset,
            end_lineno=self._end_lineno,
            end_col_offset=self._end_col,
            source_file=self._source_file,
        )
        # Safe mutation of frozen dataclass cache field (idempotent write)
        object.__setattr__(self, "_location_cache", loc)
        return loc

    def __repr__(self) -> str:
        """Compact repr for debugging."""
        val = self.value
        if len(val) > 20:
            val = val[:17] + "..."
        return f"Token({self.type.name}, {val!r}, {self._lineno}:{self._col})"

    @property
    def lineno(self) -> int:
        """Line number (convenience accessor)."""
        return self._lineno

    @property
    def col(self) -> int:
        """Column offset (convenience accessor)."""
        return self._col
