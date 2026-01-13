"""Syntax highlighting protocol and injection for Patitas.

Provides optional syntax highlighting for code blocks.
When patitas[syntax] is installed, Rosettes is used automatically.

Usage:
    # Automatic with patitas[syntax]
    from patitas import Markdown
    md = Markdown()  # Highlighting enabled if rosettes is installed
    
    # Manual injection
    from patitas.highlighting import set_highlighter
    
    def my_highlighter(code: str, language: str) -> str:
        return f'<pre class="language-{language}"><code>{code}</code></pre>'
    
    set_highlighter(my_highlighter)
"""

from __future__ import annotations

from typing import Callable, Protocol


class Highlighter(Protocol):
    """Protocol for syntax highlighters.
    
    Highlighters take code and language and return HTML markup
    with syntax highlighting applied.
    """

    def __call__(self, code: str, language: str) -> str:
        """Highlight code with syntax colors.
        
        Args:
            code: Source code to highlight
            language: Language identifier (e.g., "python", "javascript")
            
        Returns:
            HTML markup with highlighting
        """
        ...


# Global highlighter
_highlighter: Callable[[str, str], str] | None = None
_tried_rosettes: bool = False


def set_highlighter(highlighter: Callable[[str, str], str] | None) -> None:
    """Set the global syntax highlighter.
    
    Args:
        highlighter: Function that takes (code, language) and returns HTML.
            Pass None to clear the highlighter.
    """
    global _highlighter
    _highlighter = highlighter


def _try_import_rosettes() -> bool:
    """Try to import and configure Rosettes highlighter."""
    global _highlighter, _tried_rosettes
    
    if _tried_rosettes:
        return _highlighter is not None
    
    _tried_rosettes = True
    
    try:
        from rosettes import highlight as rosettes_highlight
        
        def rosettes_highlighter(code: str, language: str) -> str:
            """Rosettes-based syntax highlighter."""
            return rosettes_highlight(code, language=language)
        
        _highlighter = rosettes_highlighter
        return True
    except ImportError:
        return False


def highlight(code: str, language: str) -> str:
    """Highlight code using the configured highlighter.
    
    Falls back to plain code block if no highlighter is available.
    Automatically tries to use Rosettes if installed.
    
    Args:
        code: Source code to highlight
        language: Language identifier
        
    Returns:
        HTML markup (highlighted if available, plain otherwise)
    """
    # Try Rosettes if no highlighter is set
    if _highlighter is None:
        _try_import_rosettes()
    
    if _highlighter is not None:
        return _highlighter(code, language)
    
    # Fallback: plain code block with language class
    from html import escape
    escaped_code = escape(code)
    lang_class = f' class="language-{language}"' if language else ""
    return f"<pre><code{lang_class}>{escaped_code}</code></pre>"


def has_highlighter() -> bool:
    """Check if a syntax highlighter is available."""
    if _highlighter is not None:
        return True
    return _try_import_rosettes()
