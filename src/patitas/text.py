"""Extract plain text from Patitas AST nodes.

Provides a public API for extracting text content from any node type,
used for heading slugs, excerpts, and LLM-safe text rendering.

Example:
    >>> from patitas import parse, extract_text
    >>> doc = parse("# Hello **World**")
    >>> extract_text(doc.children[0])
    'Hello World'
"""

from patitas.nodes import (
    BlockQuote,
    CodeSpan,
    Directive,
    Document,
    Emphasis,
    FencedCode,
    FootnoteDef,
    FootnoteRef,
    Heading,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    LineBreak,
    Link,
    List,
    ListItem,
    Math,
    MathBlock,
    Node,
    Paragraph,
    Role,
    SoftBreak,
    Strikethrough,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    ThematicBreak,
)


def extract_text(node: Node, *, source: str = "") -> str:
    """Extract plain text from any AST node.

    Recursively walks the tree, concatenating text content. Skips HtmlBlock,
    HtmlInline. LineBreak and SoftBreak contribute a space.

    Args:
        node: Any AST node (block or inline).
        source: Original source string (required for FencedCode zero-copy
            extraction; use empty string if unavailable).

    Returns:
        Concatenated plain text from the node and its descendants.

    """
    match node:
        case Text():
            return node.content
        case CodeSpan():
            return node.code
        case Math():
            return node.content
        case Image():
            return node.alt
        case Role():
            return node.content
        case LineBreak() | SoftBreak():
            return " "
        case HtmlInline() | HtmlBlock():
            return ""
        case MathBlock():
            return node.content
        case FencedCode():
            try:
                return node.get_code(source)
            except (IndexError, TypeError):
                return ""
        case IndentedCode():
            return node.code
        case Emphasis() | Strong() | Strikethrough() | Link():
            return "".join(extract_text(c, source=source) for c in node.children)
        case Paragraph() | Heading() | FootnoteDef() | Directive():
            return "".join(extract_text(c, source=source) for c in node.children)
        case BlockQuote():
            return " ".join(
                extract_text(c, source=source) for c in node.children
            )
        case List():
            return " ".join(
                extract_text(item, source=source) for item in node.items
            )
        case ListItem():
            return " ".join(extract_text(c, source=source) for c in node.children)
        case Document():
            return " ".join(extract_text(c, source=source) for c in node.children)
        case Table():
            rows = list(node.head) + list(node.body)
            return " ".join(
                extract_text(cell, source=source)
                for row in rows
                for cell in row.cells
            )
        case TableRow():
            return " ".join(extract_text(c, source=source) for c in node.cells)
        case TableCell():
            return "".join(extract_text(c, source=source) for c in node.children)
        case ThematicBreak() | FootnoteRef():
            return ""
        case _:
            return ""
