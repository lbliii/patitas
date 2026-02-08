"""AST serialization — JSON round-trip for Patitas AST nodes.

Converts typed AST nodes to/from JSON-compatible dicts. Useful for:
- Caching parsed ASTs to disk (Bengal incremental builds)
- Sending AST diffs over the wire (Purr SSE)
- Debugging and inspection

All output is deterministic (sorted keys) for cache-key stability.

Example:
    from patitas import parse
    from patitas.serialization import to_json, from_json

    doc = parse("# Hello **World**")
    json_str = to_json(doc)
    restored = from_json(json_str)
    assert doc == restored

Thread Safety:
    All functions are pure — safe to call from any thread.

"""

import json
from dataclasses import fields
from typing import Any

from patitas.directives.options import DirectiveOptions
from patitas.location import SourceLocation
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

# Registry of node type names to classes for deserialization
_NODE_TYPES: dict[str, type] = {
    "Document": Document,
    "Heading": Heading,
    "Paragraph": Paragraph,
    "FencedCode": FencedCode,
    "IndentedCode": IndentedCode,
    "BlockQuote": BlockQuote,
    "List": List,
    "ListItem": ListItem,
    "ThematicBreak": ThematicBreak,
    "HtmlBlock": HtmlBlock,
    "Directive": Directive,
    "Table": Table,
    "TableRow": TableRow,
    "TableCell": TableCell,
    "MathBlock": MathBlock,
    "FootnoteDef": FootnoteDef,
    "Text": Text,
    "Emphasis": Emphasis,
    "Strong": Strong,
    "Strikethrough": Strikethrough,
    "Link": Link,
    "Image": Image,
    "CodeSpan": CodeSpan,
    "LineBreak": LineBreak,
    "SoftBreak": SoftBreak,
    "HtmlInline": HtmlInline,
    "Role": Role,
    "Math": Math,
    "FootnoteRef": FootnoteRef,
}

# Fields that contain child node tuples
_CHILDREN_FIELDS = {"children", "items", "cells", "head", "body"}


def to_dict(node: Node) -> dict[str, Any]:
    """Convert an AST node to a JSON-compatible dict.

    Includes a ``_type`` discriminator field for deserialization.
    Recursively serializes child nodes and SourceLocation objects.

    Args:
        node: Any Patitas AST node.

    Returns:
        Dict with ``_type`` and all node fields.

    """
    result: dict[str, Any] = {"_type": type(node).__name__}

    for f in fields(node):
        value = getattr(node, f.name)
        result[f.name] = _serialize_value(value, f.name)

    return result


def _serialize_value(value: Any, field_name: str = "") -> Any:
    """Serialize a single field value."""
    if isinstance(value, Node):
        return to_dict(value)
    if isinstance(value, SourceLocation):
        return {
            "_type": "SourceLocation",
            "lineno": value.lineno,
            "col_offset": value.col_offset,
            "offset": value.offset,
            "end_offset": value.end_offset,
            "end_lineno": value.end_lineno,
            "end_col_offset": value.end_col_offset,
            "source_file": value.source_file,
        }
    if isinstance(value, DirectiveOptions):
        return {
            "_type": "DirectiveOptions",
            **{f.name: getattr(value, f.name) for f in fields(value)},
        }
    if isinstance(value, tuple):
        return [_serialize_value(item, field_name) for item in value]
    if isinstance(value, frozenset):
        return sorted(value)
    # Primitives: str, int, float, bool, None
    return value


def from_dict(data: dict[str, Any]) -> Node:
    """Reconstruct a typed AST node from a dict.

    Uses the ``_type`` discriminator to determine the node class.
    Recursively deserializes child nodes and SourceLocation objects.

    Args:
        data: Dict with ``_type`` and node fields (as produced by to_dict).

    Returns:
        Typed AST node (frozen dataclass).

    Raises:
        ValueError: If ``_type`` is missing or unknown.

    """
    type_name = data.get("_type")
    if type_name is None:
        msg = "Missing '_type' field in serialized node"
        raise ValueError(msg)

    node_cls = _NODE_TYPES.get(type_name)
    if node_cls is None:
        msg = f"Unknown node type: {type_name!r}"
        raise ValueError(msg)

    kwargs: dict[str, Any] = {}
    for f in fields(node_cls):
        if f.name not in data:
            continue
        raw = data[f.name]
        kwargs[f.name] = _deserialize_value(raw, f.name)

    return node_cls(**kwargs)


def _deserialize_value(value: Any, field_name: str = "") -> Any:
    """Deserialize a single field value."""
    if isinstance(value, dict):
        type_name = value.get("_type")
        if type_name == "SourceLocation":
            return SourceLocation(
                lineno=value["lineno"],
                col_offset=value["col_offset"],
                offset=value.get("offset", 0),
                end_offset=value.get("end_offset", 0),
                end_lineno=value.get("end_lineno"),
                end_col_offset=value.get("end_col_offset"),
                source_file=value.get("source_file"),
            )
        if type_name == "DirectiveOptions":
            opts = {k: v for k, v in value.items() if k != "_type"}
            return DirectiveOptions(**opts)
        if type_name is not None:
            return from_dict(value)
        return value
    if isinstance(value, list):
        if field_name in _CHILDREN_FIELDS:
            return tuple(_deserialize_value(item, field_name) for item in value)
        # Could be a tuple of other things (e.g., alignments)
        return tuple(_deserialize_value(item, field_name) for item in value)
    return value


def to_json(doc: Document, *, indent: int | None = None) -> str:
    """Serialize a Document AST to a JSON string.

    Output is deterministic (sorted keys) for cache-key stability.

    Args:
        doc: Document to serialize.
        indent: JSON indentation level (None for compact).

    Returns:
        JSON string.

    """
    return json.dumps(to_dict(doc), sort_keys=True, indent=indent)


def from_json(data: str) -> Document:
    """Deserialize a Document AST from a JSON string.

    Args:
        data: JSON string (as produced by to_json).

    Returns:
        Document AST node.

    Raises:
        ValueError: If the JSON doesn't represent a Document.

    """
    raw = json.loads(data)
    node = from_dict(raw)
    if not isinstance(node, Document):
        msg = f"Expected Document, got {type(node).__name__}"
        raise ValueError(msg)
    return node
