"""Text processing utilities for Patitas.

Provides canonical implementations for common text operations like slugification.

Example:
    >>> from patitas.utils.text import slugify
    >>> slugify("Hello World!")
    'hello-world'
"""

from __future__ import annotations

import html as html_module
import re


def slugify(
    text: str,
    unescape_html: bool = True,
    max_length: int | None = None,
    separator: str = "-",
) -> str:
    """Convert text to URL-safe slug with Unicode support.

    Preserves Unicode word characters (letters, digits, underscore) to support
    international content. Modern web browsers and servers handle Unicode URLs.

    Args:
        text: Text to slugify
        unescape_html: Whether to decode HTML entities first (e.g., &amp; -> &)
        max_length: Maximum slug length (None = unlimited)
        separator: Character to use between words (default: '-')

    Returns:
        URL-safe slug (lowercase, with Unicode word chars and separators)

    Examples:
        >>> slugify("Hello World!")
        'hello-world'
        >>> slugify("Test & Code")
        'test-code'
        >>> slugify("Test &amp; Code", unescape_html=True)
        'test-code'
        >>> slugify("Very Long Title Here", max_length=10)
        'very-long'
        >>> slugify("你好世界")
        '你好世界'
        >>> slugify("Café")
        'café'

    Note:
        Uses Python's ``\\w`` regex pattern which includes Unicode letters and digits.
        This is intentional to support international content in URLs.
    """
    if not text:
        return ""

    # Decode HTML entities if requested
    if unescape_html:
        text = html_module.unescape(text)

    # Convert to lowercase and strip whitespace
    text = text.lower().strip()

    # Remove non-word characters (except spaces and hyphens)
    # Keep Unicode word characters (\w includes non-ASCII)
    text = re.sub(r"[^\w\s-]", "", text)

    # Replace multiple spaces/hyphens with separator
    text = re.sub(r"[-\s]+", separator, text)

    # Remove leading/trailing separators
    text = text.strip(separator)

    # Apply max length if specified
    if max_length is not None and len(text) > max_length:
        # Try to break at separator for cleaner truncation
        truncated = text[:max_length]
        if separator in truncated:
            # Find last separator before max_length
            parts = truncated.split(separator)
            text = separator.join(parts[:-1])
        else:
            text = truncated

    return text


def escape_html(text: str) -> str:
    """Escape HTML special characters for safe use in attributes.

    Converts special characters to HTML entities:
    - & becomes &amp;
    - < becomes &lt;
    - > becomes &gt;
    - " becomes &quot;
    - ' becomes &#x27;

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text safe for use in attribute values

    Examples:
        >>> escape_html("<script>alert('xss')</script>")
        "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    """
    if not text:
        return ""

    escaped = html_module.escape(text, quote=True)
    return escaped.replace("'", "&#x27;")
