"""Dropdown directive for collapsible content.

Provides collapsible sections with markdown support including
nested directives and code blocks.

Options:
:open: Start expanded (default: false)
:icon: Icon name to display next to the title
:badge: Badge text (e.g., "New", "Advanced", "Beta")
:color: Color variant (success, warning, danger, info, minimal)
:description: Secondary text below the title
:class: Additional CSS classes

Example:
:::{dropdown} Click to expand
:open:
:icon: info
:badge: New
:color: info
:description: Additional context about this content

Hidden content here with **markdown** support.
:::

Thread Safety:
Stateless handler. Safe for concurrent use across threads.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from html import escape as html_escape
from typing import TYPE_CHECKING, Any, ClassVar

from patitas.directives.contracts import DROPDOWN_CONTRACT, DirectiveContract
from patitas.directives.options import StyledOptions
from patitas.nodes import Directive

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.nodes import Block
    from patitas.stringbuilder import StringBuilder


# Valid color variants
DROPDOWN_COLORS = frozenset(["success", "warning", "danger", "info", "minimal"])


def _render_dropdown_icon(icon_name: str) -> str:
    """Render dropdown icon using icon resolver.

    Args:
        icon_name: Name of the icon to render

    Returns:
        SVG HTML string, or empty string if icon not found
    """
    from patitas.icons import get_icon

    icon_html = get_icon(icon_name)
    return icon_html or ""


@dataclass(frozen=True, slots=True)
class DropdownOptions(StyledOptions):
    """Options for dropdown directive.

    Attributes:
        open: Whether dropdown is initially open (expanded)
        icon: Icon name to display next to the title
        badge: Badge text (e.g., "New", "Advanced", "Beta")
        color: Color variant (success, warning, danger, info, minimal)
        description: Secondary text below the title
    """

    open: bool = False
    icon: str | None = None
    badge: str | None = None
    color: str | None = None
    description: str | None = None


class DropdownDirective:
    """Handler for dropdown (collapsible) directive.

    Renders collapsible content using <details>/<summary>.

    Thread Safety:
        Stateless handler. Safe for concurrent use.
    """

    names: ClassVar[tuple[str, ...]] = ("dropdown", "details")
    token_type: ClassVar[str] = "dropdown"
    contract: ClassVar[DirectiveContract | None] = DROPDOWN_CONTRACT
    options_class: ClassVar[type[DropdownOptions]] = DropdownOptions
    preserves_raw_content: ClassVar[bool] = False

    def parse(
        self,
        name: str,
        title: str | None,
        options: DropdownOptions,
        content: str,
        children: Sequence[Block],
        location: SourceLocation,
    ) -> Directive[DropdownOptions]:
        """Build dropdown AST node."""
        effective_title = title or "Details"

        return Directive(
            location=location,
            name=name,
            title=effective_title,
            options=options,
            children=tuple(children),
        )

    def render(
        self,
        node: Directive[DropdownOptions],
        rendered_children: str,
        sb: StringBuilder,
    ) -> None:
        """Render dropdown to HTML.

        Args:
            node: Directive AST node
            rendered_children: Pre-rendered child content
            sb: StringBuilder for output
        """
        opts = node.options
        title = node.title or "Details"
        is_open = opts.open
        icon = opts.icon or ""
        badge = opts.badge or ""
        color = opts.color or ""
        description = opts.description or ""
        css_class = opts.class_ or ""

        # Add color variant to class string if valid
        if color and color in DROPDOWN_COLORS:
            css_class = f"{color} {css_class}".strip() if css_class else color

        # Build class string
        class_parts = ["dropdown"]
        if css_class:
            class_parts.append(css_class)
        class_str = " ".join(class_parts)

        # Build summary content with optional icon, description, and badge
        summary_parts = []

        # Add icon if specified
        if icon:
            icon_html = _render_dropdown_icon(icon)
            if icon_html:
                summary_parts.append(f'<span class="dropdown-icon">{icon_html}</span>')

        # Build title block (title + optional description)
        title_block = f'<span class="dropdown-title">{html_escape(title)}</span>'
        if description:
            title_block += f'<span class="dropdown-description">{html_escape(description)}</span>'
        summary_parts.append(f'<span class="dropdown-header">{title_block}</span>')

        # Add badge if specified
        if badge:
            summary_parts.append(f'<span class="dropdown-badge">{html_escape(badge)}</span>')

        summary_content = "".join(summary_parts)

        # Build open attribute
        open_attr = " open" if is_open else ""

        # Output HTML
        sb.append(f'<details class="{html_escape(class_str)}"{open_attr}>\n')
        sb.append(f"  <summary>{summary_content}</summary>\n")
        sb.append('  <div class="dropdown-content">\n')
        sb.append(rendered_children)
        sb.append("  </div>\n")
        sb.append("</details>\n")
