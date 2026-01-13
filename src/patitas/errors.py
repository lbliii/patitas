"""Exception classes for Patitas.

Provides standardized exceptions for error handling throughout Patitas.
"""

from __future__ import annotations


class PatitasError(Exception):
    """Base exception for all Patitas errors.
    
    Subclass this for specific error categories.
    """

    pass


class ParseError(PatitasError):
    """Error during Markdown parsing.
    
    Raised when the parser encounters invalid or unexpected input.
    """

    def __init__(
        self,
        message: str,
        lineno: int | None = None,
        col_offset: int | None = None,
        source_file: str | None = None,
    ) -> None:
        """Initialize parse error with optional location.
        
        Args:
            message: Error description
            lineno: Line number where error occurred (1-indexed)
            col_offset: Column offset where error occurred (1-indexed)
            source_file: Path to source file (optional)
        """
        self.message = message
        self.lineno = lineno
        self.col_offset = col_offset
        self.source_file = source_file

        # Build formatted message
        location = ""
        if source_file:
            location = f"{source_file}:"
        if lineno is not None:
            location += f"{lineno}:"
            if col_offset is not None:
                location += f"{col_offset}:"
        if location:
            location = location.rstrip(":") + " "

        super().__init__(f"{location}{message}")


class DirectiveContractError(PatitasError):
    """Error when a directive contract is violated.
    
    Raised when directive options don't meet requirements or
    content doesn't match expected structure.
    """

    def __init__(
        self,
        directive_name: str,
        message: str,
        lineno: int | None = None,
    ) -> None:
        """Initialize directive contract error.
        
        Args:
            directive_name: Name of the directive (e.g., "note", "code-tabs")
            message: Description of the contract violation
            lineno: Line number where directive started (optional)
        """
        self.directive_name = directive_name
        self.lineno = lineno

        location = f" (line {lineno})" if lineno else ""
        super().__init__(f"Directive '{directive_name}'{location}: {message}")


class RenderError(PatitasError):
    """Error during HTML rendering.
    
    Raised when the renderer encounters an invalid AST node
    or fails to produce valid output.
    """

    pass


class PluginError(PatitasError):
    """Error in plugin initialization or execution.
    
    Raised when a plugin fails to register or process content.
    """

    def __init__(self, plugin_name: str, message: str) -> None:
        """Initialize plugin error.
        
        Args:
            plugin_name: Name of the failing plugin
            message: Description of the error
        """
        self.plugin_name = plugin_name
        super().__init__(f"Plugin '{plugin_name}': {message}")
