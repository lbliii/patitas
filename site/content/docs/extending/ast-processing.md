---
title: AST Processing
description: Visit and transform the Markdown AST
draft: false
weight: 40
lang: en
type: doc
tags:
- extending
- visitor
- transform
- ast
keywords:
- visitor
- transform
- ast
- rewrite
- traverse
category: how-to
icon: tree
---

# AST Processing

Patitas provides two tools for working with the AST after parsing:
`BaseVisitor` for reading the tree and `transform()` for rewriting it.

## BaseVisitor

A visitor walks the AST and dispatches to typed `visit_*` methods. Override
the methods for node types you care about — everything else falls through
to `visit_default`.

### Collect All Headings

```python
from patitas import parse, BaseVisitor, Heading

class HeadingCollector(BaseVisitor[None]):
    def __init__(self) -> None:
        self.headings: list[Heading] = []

    def visit_heading(self, node: Heading) -> None:
        self.headings.append(node)

doc = parse(source)
collector = HeadingCollector()
collector.visit(doc)

for h in collector.headings:
    print(f"{'#' * h.level} (line {h.location.lineno})")
```

### Extract All Links

```python
from patitas import parse, BaseVisitor, Link

class LinkExtractor(BaseVisitor[None]):
    def __init__(self) -> None:
        self.urls: list[str] = []

    def visit_link(self, node: Link) -> None:
        self.urls.append(node.url)

doc = parse(source)
extractor = LinkExtractor()
extractor.visit(doc)

for url in extractor.urls:
    print(url)
```

### Count All Nodes

```python
from patitas import parse, BaseVisitor

class NodeCounter(BaseVisitor[None]):
    def __init__(self) -> None:
        self.count: int = 0

    def visit_default(self, node) -> None:
        self.count += 1

doc = parse(source)
counter = NodeCounter()
counter.visit(doc)
print(f"{counter.count} nodes in the AST")
```

### How Dispatch Works

`BaseVisitor` uses `match` to dispatch to the correct method:

1. Call `visit(node)` on any node
2. The visitor matches the node type and calls `visit_heading`, `visit_paragraph`, etc.
3. Children are walked automatically after the visit method returns
4. Unmatched types call `visit_default`

Available visit methods (one per node type):

| Block nodes | Inline nodes |
|---|---|
| `visit_document` | `visit_text` |
| `visit_heading` | `visit_emphasis` |
| `visit_paragraph` | `visit_strong` |
| `visit_fenced_code` | `visit_strikethrough` |
| `visit_indented_code` | `visit_link` |
| `visit_block_quote` | `visit_image` |
| `visit_list` | `visit_code_span` |
| `visit_list_item` | `visit_line_break` |
| `visit_thematic_break` | `visit_soft_break` |
| `visit_html_block` | `visit_html_inline` |
| `visit_directive` | `visit_role` |
| `visit_table` | `visit_math` |
| `visit_table_row` | `visit_footnote_ref` |
| `visit_table_cell` | |
| `visit_math_block` | |
| `visit_footnote_def` | |

### Thread Safety

Visitors accumulate mutable state, so create a new instance per thread:

```python
from concurrent.futures import ThreadPoolExecutor

def count_headings(source: str) -> int:
    doc = parse(source)
    collector = HeadingCollector()  # New instance per thread
    collector.visit(doc)
    return len(collector.headings)

with ThreadPoolExecutor(max_workers=4) as pool:
    counts = list(pool.map(count_headings, sources))
```

## transform()

`transform()` rewrites the AST immutably. It applies a function to every
node bottom-up (children first, then parent) and returns a new tree. The
original is untouched.

```python
def transform(doc: Document, fn: Callable[[Node], Node]) -> Document
```

**Parameters:**
- `doc`: The Document to transform
- `fn`: Function that receives a node and returns a (possibly new) node.
  Return the same node to keep it unchanged.

**Returns:** A new Document with the transformation applied.

### Shift Heading Levels

Demote all headings by one level (useful when embedding a document as a
subsection):

```python
import dataclasses
from patitas import parse, transform, Heading
from patitas.nodes import Node

def shift_headings(node: Node) -> Node:
    if isinstance(node, Heading):
        return dataclasses.replace(node, level=min(node.level + 1, 6))
    return node

doc = parse("# Title\n## Section")
new_doc = transform(doc, shift_headings)
# Title is now level 2, Section is now level 3
```

### Rewrite Links

Convert relative links to absolute:

```python
import dataclasses
from patitas import parse, transform, Link
from patitas.nodes import Node

BASE_URL = "https://example.com"

def absolutize_links(node: Node) -> Node:
    if isinstance(node, Link) and node.url.startswith("/"):
        return dataclasses.replace(node, url=BASE_URL + node.url)
    return node

doc = parse("[About](/about)")
new_doc = transform(doc, absolutize_links)
```

### How It Works

1. The function walks the tree bottom-up
2. Children are transformed first, then the parent
3. If a node is unchanged (`fn` returns the same object), no allocation occurs
4. If children are all unchanged, the parent keeps its original tuple
5. Only modified paths allocate new nodes via `dataclasses.replace()`

This means an identity transform (returning every node unchanged) is fast —
it walks the tree but allocates nothing.

### Thread Safety

`transform()` is a pure function. The input tree is never modified, and the
output is a new frozen tree. Safe to call from any thread.

## Combining Visitor and Transform

A common pattern: use a visitor to analyze the tree, then a transform to
rewrite it based on what you found.

```python
from patitas import parse, render, BaseVisitor, transform, Heading
from patitas.nodes import Node

# Step 1: Find the deepest heading level
class MaxLevel(BaseVisitor[None]):
    def __init__(self) -> None:
        self.max: int = 0

    def visit_heading(self, node: Heading) -> None:
        self.max = max(self.max, node.level)

doc = parse(source)

finder = MaxLevel()
finder.visit(doc)

# Step 2: Normalize all headings to start at level 1
offset = finder.max - 1

def normalize(node: Node) -> Node:
    if isinstance(node, Heading) and node.level > 1:
        import dataclasses
        return dataclasses.replace(node, level=max(1, node.level - offset))
    return node

normalized = transform(doc, normalize)
html = render(normalized, source=source)
```

## Performance

Both operations are fast relative to parsing:

- **Visitor**: ~0.7 us/node — traversal with match dispatch
- **Identity transform**: ~0.4 ms for a 1000-node tree (no allocations)
- **Rewriting transform**: ~0.5 ms for a 1000-node tree (selective allocations)

Parse once, then visit and transform cheaply on the frozen AST.
