"""Typed AST — collect headings for a table of contents."""

from patitas import parse
from patitas.nodes import Heading
from patitas.visitor import BaseVisitor


def _heading_text(node: Heading) -> str:
    """Extract plain text from heading inline children."""
    parts: list[str] = []
    for child in node.children:
        if hasattr(child, "content"):
            parts.append(child.content)
        else:
            parts.append(_inline_text(child))
    return "".join(parts)


def _inline_text(node) -> str:
    """Recursively extract text from inline nodes."""
    if hasattr(node, "content"):
        return node.content
    if hasattr(node, "children"):
        return "".join(_inline_text(c) for c in node.children)
    return ""


class TocCollector(BaseVisitor[None]):
    """Collect headings for a table of contents."""

    def __init__(self) -> None:
        self.headings: list[tuple[int, str]] = []

    def visit_heading(self, node: Heading) -> None:
        text = _heading_text(node)
        self.headings.append((node.level, text))


source = """# Introduction

Welcome to the guide.

## Getting Started

First steps.

### Installation

How to install.

## Advanced Topics

Deep dive.
"""

doc = parse(source)
collector = TocCollector()
collector.visit(doc)

print("Table of Contents:")
for level, text in collector.headings:
    indent = "  " * (level - 1)
    print(f"{indent}{'#' * level} {text}")
