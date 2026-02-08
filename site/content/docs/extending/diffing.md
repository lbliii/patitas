---
title: AST Diffing
description: Structural diff on frozen AST trees
draft: false
weight: 30
lang: en
type: doc
tags:
- extending
- diffing
- ast
keywords:
- diff
- ast
- incremental
- changes
category: how-to
icon: git-compare
---

# AST Diffing

Compare two Document trees and get a changeset describing what was added,
removed, or modified. Built on frozen dataclasses, so identical subtrees
are skipped in O(1).

## Quick Start

```python
from patitas import parse, diff_documents

old_doc = parse("# Hello\nWorld")
new_doc = parse("# Hello\nUpdated world")

changes = diff_documents(old_doc, new_doc)
for change in changes:
    print(f"{change.kind} at {change.path}")
```

## diff_documents()

```python
def diff_documents(old: Document, new: Document) -> tuple[ASTChange, ...]
```

**Parameters:**
- `old`: The original Document AST
- `new`: The modified Document AST

**Returns:** Tuple of `ASTChange` objects describing the differences.

Thread-safe — this is a pure function with no shared state.

## ASTChange

Each change is a frozen dataclass:

```python
@dataclass(frozen=True, slots=True)
class ASTChange:
    kind: Literal["added", "removed", "modified"]
    path: tuple[int, ...]
    old_node: object | None
    new_node: object | None
```

- `kind` — the type of change
- `path` — position in the tree as child indices (e.g., `(2, 0)` means
  third child of root, first child of that node)
- `old_node` — the node before the change (`None` for additions)
- `new_node` — the node after the change (`None` for removals)

## How It Works

The differ walks both trees in parallel by child index:

1. If nodes are equal (`==`), skip the subtree — frozen nodes make this O(1)
2. If nodes are the same type but different content, emit `modified`
3. If nodes are different types, emit `removed` + `added`
4. If one tree has more children, emit `added` or `removed` for the extras

This is a positional diff on ordered tuples, not a generic tree edit distance
algorithm. It's fast because it leverages the known AST schema.

## Use Cases

### Incremental Builds

Only re-render pages whose AST actually changed:

```python
from patitas import parse, render, diff_documents

# Parse new version
new_doc = parse(new_source)

# Compare against cached AST
changes = diff_documents(cached_doc, new_doc)

if changes:
    # Content changed — re-render
    html = render(new_doc, source=new_source)
    update_cache(new_doc, html)
else:
    # Identical — skip rendering entirely
    html = cached_html
```

### Change Detection

Find which sections of a document were edited:

```python
from patitas import parse, diff_documents, Heading

old_doc = parse(old_source)
new_doc = parse(new_source)

for change in diff_documents(old_doc, new_doc):
    if change.kind == "modified":
        node = change.new_node
        if isinstance(node, Heading):
            print(f"Heading changed at position {change.path}")
    elif change.kind == "added":
        print(f"New content at position {change.path}")
```

### Live Preview

In an editor with live preview, diff the AST to determine whether a
re-render is needed:

```python
previous_doc = parse(previous_source)
current_doc = parse(current_source)

if diff_documents(previous_doc, current_doc):
    # Something changed — update the preview
    update_preview(render(current_doc, source=current_source))
```

## Performance

The frozen-node fast path makes diffing significantly cheaper than
re-parsing:

- **Identical trees**: ~0.002 ms (single equality check on the root)
- **Small changes**: ~0.01 ms for a few modified blocks
- **Large documents (100+ blocks)**: ~0.2 ms with scattered changes

Diffing is typically 15–60x faster than parsing the same document.
