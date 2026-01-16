"""Icon role handler.

Provides inline SVG icon support via {icon}`name` syntax.
The icon resolver can be configured per-instance for registry isolation.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, ClassVar

from patitas.nodes import Role

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.stringbuilder import StringBuilder


class IconRole:
    """Role for inline SVG icons.

    Icon rendering requires a resolver function that maps icon names to SVG.
    Without a resolver, this role renders placeholder text.

    Usage (with resolver configured):
        {icon}`github` → <svg>...</svg>
        {icon}`check` → <svg>...</svg>

    Usage (without resolver):
        {icon}`github` → [icon:github]

    Thread Safety:
        Instance-level resolver ensures registry isolation.
        Safe for concurrent use when resolver is thread-safe.
    """

    names: ClassVar[tuple[str, ...]] = ("icon",)
    token_type: ClassVar[str] = "icon"

    __slots__ = ("_resolver",)

    def __init__(
        self,
        resolver: Callable[[str], str | None] | None = None,
    ) -> None:
        """Initialize IconRole with optional resolver.

        Args:
            resolver: Function that takes icon name and returns SVG string or None.
                     If None, icons render as placeholder text.
        """
        self._resolver = resolver

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Build the icon role AST node.

        Args:
            name: The role name ("icon")
            content: Icon name (e.g., "github", "check")
            location: Source location for error reporting

        Returns:
            A Role node for the AST
        """
        return Role(location=location, name=name, content=content)

    def render(self, node: Role, sb: StringBuilder) -> None:
        """Render icon role to HTML.

        Args:
            node: The Role AST node to render
            sb: StringBuilder to append output to
        """
        content = node.content
        if self._resolver is not None:
            svg = self._resolver(content)
            if svg:
                sb.append(svg)
                return

        # Fallback: render as text placeholder
        sb.append(f'<span class="icon-placeholder">[icon:{content}]</span>')
