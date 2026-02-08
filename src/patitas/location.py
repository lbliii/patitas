"""Source location tracking for error messages and debugging.

Provides SourceLocation dataclass for tracking positions in source text.
Used throughout Patitas for error messages, AST nodes, and debugging.

Thread Safety:
SourceLocation is frozen (immutable) and safe to share across threads.

"""

from dataclasses import dataclass

# Module-level singleton (created once at import or on first use)
_UNKNOWN_LOCATION: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class SourceLocation:
    # ... (existing attributes) ...
    lineno: int
    col_offset: int
    offset: int = 0  # NEW: Absolute start offset in source buffer
    end_offset: int = 0  # NEW: Absolute end offset in source buffer
    end_lineno: int | None = None
    end_col_offset: int | None = None
    source_file: str | None = None

    def __str__(self) -> str:
        """Format location for error messages.

        Returns:
            Formatted string like "file.md:10:5" or "10:5"
        """
        if self.source_file:
            return f"{self.source_file}:{self.lineno}:{self.col_offset}"
        return f"{self.lineno}:{self.col_offset}"

    def span_to(self, end: SourceLocation) -> SourceLocation:
        """Create a new location spanning from this location to end.

        Args:
            end: Ending location

        Returns:
            New SourceLocation with this start and end's end positions
        """
        return SourceLocation(
            lineno=self.lineno,
            col_offset=self.col_offset,
            offset=self.offset,
            end_offset=end.end_offset or end.offset,
            end_lineno=end.end_lineno or end.lineno,
            end_col_offset=end.end_col_offset or end.col_offset,
            source_file=self.source_file,
        )

    @classmethod
    def unknown(cls) -> SourceLocation:
        """Create an unknown/placeholder location.

        Use for AST nodes created synthetically or when location is unavailable.
        """
        global _UNKNOWN_LOCATION
        if _UNKNOWN_LOCATION is None:
            _UNKNOWN_LOCATION = cls(lineno=0, col_offset=0)
        return _UNKNOWN_LOCATION
