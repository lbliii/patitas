"""Content-aware context mapping for Patitas AST nodes.

Maps AST node types to the template context paths they affect. This defines
how content structure maps to template variables, enabling reactive systems
(like Purr) to determine which template blocks need re-rendering when
specific content nodes change.

The mapping is conservative — it may over-identify affected context paths
(causing unnecessary re-renders) but never under-identify (causing stale
content). When a node type isn't in the map, the fallback covers it.

Example:
    from patitas.context import context_paths_for
    from patitas.nodes import Heading

    paths = context_paths_for(heading_node)
    # frozenset({"page.toc", "page.headings", "page.body"})

Thread Safety:
    All data is immutable (frozensets). Safe to call from any thread.

"""

from patitas.nodes import Node

# Maps Patitas AST node type names to the template context paths they affect.
CONTENT_CONTEXT_MAP: dict[str, frozenset[str]] = {
    "Heading": frozenset({"page.toc", "page.headings", "page.body"}),
    "Paragraph": frozenset({"page.body"}),
    "FencedCode": frozenset({"page.body"}),
    "IndentedCode": frozenset({"page.body"}),
    "List": frozenset({"page.body"}),
    "ListItem": frozenset({"page.body"}),
    "BlockQuote": frozenset({"page.body"}),
    "Table": frozenset({"page.body"}),
    "ThematicBreak": frozenset({"page.body"}),
    "Directive": frozenset({"page.body"}),
    "MathBlock": frozenset({"page.body"}),
    "FootnoteDef": frozenset({"page.body", "page.footnotes"}),
    "HtmlBlock": frozenset({"page.body"}),
}

# Catch-all for unknown or unrecognized node types — conservative.
FALLBACK_CONTEXT_PATHS: frozenset[str] = frozenset({"page.body", "page.toc", "page.meta"})


def context_paths_for(node: Node) -> frozenset[str]:
    """Return the template context paths affected by this node type.

    Uses the node's class name to look up affected paths. Returns the
    conservative fallback for unknown node types.

    Args:
        node: Any Patitas AST node.

    Returns:
        Frozenset of context path strings (e.g., ``"page.toc"``).

    """
    return CONTENT_CONTEXT_MAP.get(type(node).__name__, FALLBACK_CONTEXT_PATHS)
