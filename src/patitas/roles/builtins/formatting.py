"""Formatting roles for inline styling.

Provides roles for common inline formatting:
- kbd: Keyboard shortcuts
- abbr: Abbreviations with expansion
- sub: Subscript
- sup: Superscript

Example:
Press {kbd}`Ctrl+C` to copy.
The {abbr}`HTML (HyperText Markup Language)` standard.
H{sub}`2`O is water.
E = mc{sup}`2`.

"""

from html import escape as html_escape
from typing import TYPE_CHECKING, ClassVar

from patitas.nodes import Role

if TYPE_CHECKING:
    from patitas.location import SourceLocation
    from patitas.stringbuilder import StringBuilder


class KbdRole:
    """Handler for {kbd}`key` role.

    Renders keyboard shortcuts with proper semantics.

    Syntax:
        {kbd}`Ctrl+C` - Single shortcut
        {kbd}`Ctrl+Shift+P` - Multiple modifiers
        {kbd}`+` or {kbd}`Plus` - The plus key itself

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("kbd",)
    token_type: ClassVar[str] = "kbd"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse kbd role content."""
        return Role(
            location=location,
            name=name,
            content=content.strip(),
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render keyboard shortcut.

        Wraps each key in <kbd> tags for proper semantics.
        Handles + as key separator, with special handling for the + key itself.
        """
        content = node.content

        # Handle single "+" key or no separator
        if content == "+" or "+" not in content:
            sb.append(f"<kbd>{html_escape(content)}</kbd>")
            return

        # Split by + to wrap individual keys, handling empty parts as literal +
        keys = content.split("+")
        parts: list[str] = []
        i = 0
        while i < len(keys):
            key = keys[i].strip()
            if key:
                parts.append(f"<kbd>{html_escape(key)}</kbd>")
            elif i + 1 < len(keys) and not keys[i + 1].strip():
                # Two consecutive empty parts = literal + key (from "++")
                parts.append("<kbd>+</kbd>")
                i += 1  # Skip the next empty part
            # Single empty part at edges is ignored (leading/trailing +)
            i += 1

        sb.append("+".join(parts))


class AbbrRole:
    """Handler for {abbr}`ABBR (expansion)` role.

    Renders abbreviations with title attribute for expansion.

    Syntax:
        {abbr}`HTML (HyperText Markup Language)`

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("abbr",)
    token_type: ClassVar[str] = "abbr"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse abbr role content.

        Extracts abbreviation and expansion from "ABBR (expansion)" format.
        """
        content = content.strip()
        abbr = content
        expansion = None

        # Parse "ABBR (expansion)" format
        if "(" in content and content.endswith(")"):
            paren_pos = content.rfind("(")
            abbr = content[:paren_pos].strip()
            expansion = content[paren_pos + 1 : -1].strip()

        return Role(
            location=location,
            name=name,
            content=abbr,
            target=expansion,
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render abbreviation with title."""
        abbr = node.content
        expansion = node.target

        if expansion:
            sb.append(f'<abbr title="{html_escape(expansion)}">')
            sb.append(html_escape(abbr))
            sb.append("</abbr>")
        else:
            sb.append(f"<abbr>{html_escape(abbr)}</abbr>")


class SubRole:
    """Handler for {sub}`text` role.

    Renders subscript text.

    Syntax:
        H{sub}`2`O

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("sub",)
    token_type: ClassVar[str] = "sub"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse sub role content."""
        return Role(
            location=location,
            name=name,
            content=content.strip(),
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render subscript."""
        sb.append(f"<sub>{html_escape(node.content)}</sub>")


class SupRole:
    """Handler for {sup}`text` role.

    Renders superscript text.

    Syntax:
        E = mc{sup}`2`

    Thread Safety:
        Stateless handler. Safe for concurrent use.

    """

    names: ClassVar[tuple[str, ...]] = ("sup",)
    token_type: ClassVar[str] = "sup"

    def parse(
        self,
        name: str,
        content: str,
        location: SourceLocation,
    ) -> Role:
        """Parse sup role content."""
        return Role(
            location=location,
            name=name,
            content=content.strip(),
        )

    def render(
        self,
        node: Role,
        sb: StringBuilder,
    ) -> None:
        """Render superscript."""
        sb.append(f"<sup>{html_escape(node.content)}</sup>")
