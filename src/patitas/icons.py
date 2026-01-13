"""Icon resolver protocol and injection for Patitas.

Provides optional icon support for directives. Icons are rendered
as placeholders unless an icon resolver is injected.

Usage:
    # With patitas[bengal] or custom resolver
    from patitas.icons import set_icon_resolver

    def my_resolver(name: str) -> str | None:
        return f'<svg class="icon icon-{name}">...</svg>'

    set_icon_resolver(my_resolver)

Without a resolver, directives render without icons (CSS class only).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol


class IconResolver(Protocol):
    """Protocol for icon resolvers.

    Icon resolvers take an icon name and return SVG markup
    or None if the icon is not found.
    """

    def __call__(self, name: str) -> str | None:
        """Resolve icon name to SVG markup.

        Args:
            name: Icon name (e.g., "github", "warning", "check")

        Returns:
            SVG markup string, or None if icon not found
        """
        ...


# Global icon resolver
_icon_resolver: Callable[[str], str | None] | None = None


def set_icon_resolver(resolver: Callable[[str], str | None] | None) -> None:
    """Set the global icon resolver.

    Args:
        resolver: Function that takes icon name and returns SVG or None.
            Pass None to clear the resolver.

    Example:
        >>> set_icon_resolver(lambda name: f'<svg>{name}</svg>')
        >>> get_icon("check")
        '<svg>check</svg>'
    """
    global _icon_resolver
    _icon_resolver = resolver


def get_icon(name: str) -> str | None:
    """Get icon SVG by name using the global resolver.

    Args:
        name: Icon name

    Returns:
        SVG markup if resolver is set and icon exists, None otherwise
    """
    if _icon_resolver is not None:
        return _icon_resolver(name)
    return None


def get_icon_or_placeholder(name: str) -> str:
    """Get icon SVG or a placeholder span.

    Args:
        name: Icon name

    Returns:
        SVG markup if available, otherwise a placeholder span
    """
    icon = get_icon(name)
    if icon:
        return icon
    return f'<span class="icon icon-{name}"></span>'


def has_icon_resolver() -> bool:
    """Check if an icon resolver is configured."""
    return _icon_resolver is not None
