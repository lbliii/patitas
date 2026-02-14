"""Immutable AST transform — shift all heading levels by 1."""

import dataclasses

from patitas import parse, render, transform
from patitas.nodes import Heading


def shift_headings(node) -> object:
    """Shift heading levels down (e.g. # -> ##)."""
    if isinstance(node, Heading):
        return dataclasses.replace(node, level=min(node.level + 1, 6))
    return node


source = """# Top Level

Content here.

## Section

More content.

### Subsection

Details.
"""

doc = parse(source)
new_doc = transform(doc, shift_headings)

print("Original:")
print(render(doc))
print()
print("After shifting headings (+1 level):")
print(render(new_doc))
