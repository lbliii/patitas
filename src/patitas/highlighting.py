"""Syntax highlighting protocol and injection for Patitas.

Provides optional syntax highlighting for code blocks.
When patitas[syntax] is installed, Rosettes is used automatically.

Protocol Alignment:
    The Highlighter protocol is aligned with Bengal's HighlightService
    for seamless integration. Both interfaces support:
    - highlight(code, language, hl_lines, show_linenos) -> str
    - supports_language(language) -> bool

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

from collections.abc import Callable
from typing import Protocol


class Highlighter(Protocol):
    """Protocol for syntax highlighters.

    Aligned with Bengal's HighlightService for seamless integration.
    Highlighters take code and language and return HTML markup
    with syntax highlighting applied.

    Thread Safety:
        Implementations must be thread-safe. The highlight() method
        may be called concurrently from multiple render threads.
    """

    def highlight(
        self,
        code: str,
        language: str,
        *,
        hl_lines: list[int] | None = None,
        show_linenos: bool = False,
    ) -> str:
        """Highlight code with syntax colors.

        Args:
            code: Source code to highlight
            language: Language identifier (e.g., "python", "javascript")
            hl_lines: 1-indexed line numbers to emphasize (optional)
            show_linenos: Include line numbers in output

        Returns:
            HTML markup with highlighting

        Contract:
            - MUST return valid HTML (never raise for bad input)
            - MUST escape HTML entities in code
            - MUST use CSS classes (not inline styles)
            - SHOULD fall back to plain text for unknown languages
        """
        ...

    def supports_language(self, language: str) -> bool:
        """Check if highlighter supports the given language.

        Args:
            language: Language identifier or alias

        Returns:
            True if highlighting is available

        Contract:
            - MUST NOT raise exceptions
            - SHOULD handle common aliases (js -> javascript)
        """
        ...


# Support for simple callable-based highlighters
SimpleHighlighter = Callable[[str, str], str]

# Global highlighter
_highlighter: Highlighter | SimpleHighlighter | None = None
_tried_rosettes: bool = False


def set_highlighter(highlighter: Highlighter | SimpleHighlighter | None) -> None:
    """Set the global syntax highlighter.

    Args:
        highlighter: A Highlighter protocol implementation, or a simple
            function that takes (code, language) and returns HTML.
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
        import rosettes  # type: ignore[import-not-found]

        class RosettesHighlighter:
            """Rosettes-based syntax highlighter implementing Highlighter protocol."""

            def highlight(
                self,
                code: str,
                language: str,
                *,
                hl_lines: list[int] | None = None,
                show_linenos: bool = False,
            ) -> str:
                """Highlight code using Rosettes."""
                hl_set = set(hl_lines) if hl_lines else None
                result: str = rosettes.highlight(
                    code,
                    language=language,
                    hl_lines=hl_set,
                    show_linenos=show_linenos,
                )
                return result

            def supports_language(self, language: str) -> bool:
                """Check if Rosettes supports the language."""
                try:
                    result: bool = rosettes.supports_language(language)
                    return result
                except Exception:
                    return False

        _highlighter = RosettesHighlighter()
        return True
    except ImportError:
        return False


def highlight(
    code: str,
    language: str,
    *,
    hl_lines: list[int] | None = None,
    show_linenos: bool = False,
) -> str:
    """Highlight code using the configured highlighter.

    Falls back to plain code block if no highlighter is available.
    Automatically tries to use Rosettes if installed.

    Args:
        code: Source code to highlight
        language: Language identifier
        hl_lines: 1-indexed line numbers to emphasize (optional)
        show_linenos: Include line numbers in output

    Returns:
        HTML markup (highlighted if available, plain otherwise)
    """
    # Try Rosettes if no highlighter is set
    if _highlighter is None:
        _try_import_rosettes()

    if _highlighter is not None:
        # Check if it's the full protocol or a simple callable
        if hasattr(_highlighter, "highlight") and callable(_highlighter.highlight):
            return _highlighter.highlight(
                code, language, hl_lines=hl_lines, show_linenos=show_linenos
            )
        elif callable(_highlighter):
            # Simple callable - just pass code and language
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


def get_highlighter() -> Highlighter | SimpleHighlighter | None:
    """Get the current highlighter instance.

    Returns:
        The configured highlighter, or None if not set.
        Automatically tries to load Rosettes if not already configured.
    """
    if _highlighter is None:
        _try_import_rosettes()
    return _highlighter
