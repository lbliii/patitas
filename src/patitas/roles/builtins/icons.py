"""Icon role handler.

STUB: This is a placeholder for icon role functionality.
The full implementation requires an icon resolver from Bengal.

For full icon support, install patitas[bengal].
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from patitas.roles.protocol import RoleHandler

if TYPE_CHECKING:
    from patitas.nodes import Inline
    from patitas.location import SourceLocation


class IconRole(RoleHandler):
    """Role for inline SVG icons.
    
    STUB: Icon rendering requires an icon resolver.
    Without patitas[bengal], this role renders the icon name as text.
    
    Usage (with patitas[bengal]):
        {icon}`github` → <svg>...</svg>
        {icon}`check` → <svg>...</svg>
    
    Usage (without icon resolver):
        {icon}`github` → [icon:github]
    """

    name = "icon"
    
    # Optional icon resolver - set by Bengal adapter
    _resolver: Callable[[str], str | None] | None = None

    @classmethod
    def set_resolver(cls, resolver: Callable[[str], str | None]) -> None:
        """Set the icon resolver function.
        
        Args:
            resolver: Function that takes icon name and returns SVG string or None
        """
        cls._resolver = resolver

    def render(self, content: str, location: SourceLocation) -> str:
        """Render icon role to HTML.
        
        Args:
            content: Icon name (e.g., "github", "check")
            location: Source location for error reporting
            
        Returns:
            HTML string (SVG if resolver available, placeholder otherwise)
        """
        if self._resolver is not None:
            svg = self._resolver(content)
            if svg:
                return svg
        
        # Fallback: render as text placeholder
        return f'<span class="icon-placeholder">[icon:{content}]</span>'
