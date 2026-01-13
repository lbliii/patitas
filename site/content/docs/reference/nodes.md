---
title: AST Nodes
description: AST node types and structure
draft: false
weight: 20
lang: en
type: doc
tags:
- reference
- ast
- nodes
keywords:
- ast
- nodes
- blocks
- inline
category: reference
icon: git-branch
---

# AST Nodes

Patitas parses Markdown into a typed Abstract Syntax Tree (AST).

All nodes are frozen dataclasses with slots for memory efficiency and thread safety.

## Block Nodes

Block nodes form the document structure.

### Document

The root node (not typically used directly).

```python
@dataclass(frozen=True, slots=True)
class Document:
    children: tuple[Block, ...]
    source_file: str | None = None
```

### Heading

```python
@dataclass(frozen=True, slots=True)
class Heading:
    level: int  # 1-6
    children: tuple[Inline, ...]
    location: SourceLocation | None = None
```

### Paragraph

```python
@dataclass(frozen=True, slots=True)
class Paragraph:
    children: tuple[Inline, ...]
    location: SourceLocation | None = None
```

### List

```python
@dataclass(frozen=True, slots=True)
class List:
    ordered: bool
    start: int | None  # For ordered lists
    tight: bool
    children: tuple[ListItem, ...]
    location: SourceLocation | None = None
```

### ListItem

```python
@dataclass(frozen=True, slots=True)
class ListItem:
    children: tuple[Block, ...]
    location: SourceLocation | None = None
```

### BlockQuote

```python
@dataclass(frozen=True, slots=True)
class BlockQuote:
    children: tuple[Block, ...]
    location: SourceLocation | None = None
```

### CodeBlock

```python
@dataclass(frozen=True, slots=True)
class CodeBlock:
    info: str  # Language hint
    literal: str  # Code content
    location: SourceLocation | None = None
```

### ThematicBreak

```python
@dataclass(frozen=True, slots=True)
class ThematicBreak:
    location: SourceLocation | None = None
```

### HtmlBlock

```python
@dataclass(frozen=True, slots=True)
class HtmlBlock:
    literal: str
    location: SourceLocation | None = None
```

## Inline Nodes

Inline nodes appear within blocks.

### Text

```python
@dataclass(frozen=True, slots=True)
class Text:
    literal: str
    location: SourceLocation | None = None
```

### Emphasis

```python
@dataclass(frozen=True, slots=True)
class Emphasis:
    children: tuple[Inline, ...]
    location: SourceLocation | None = None
```

### Strong

```python
@dataclass(frozen=True, slots=True)
class Strong:
    children: tuple[Inline, ...]
    location: SourceLocation | None = None
```

### Code

Inline code span.

```python
@dataclass(frozen=True, slots=True)
class Code:
    literal: str
    location: SourceLocation | None = None
```

### Link

```python
@dataclass(frozen=True, slots=True)
class Link:
    destination: str
    title: str
    children: tuple[Inline, ...]
    location: SourceLocation | None = None
```

### Image

```python
@dataclass(frozen=True, slots=True)
class Image:
    destination: str
    title: str
    alt: str
    location: SourceLocation | None = None
```

### SoftBreak

```python
@dataclass(frozen=True, slots=True)
class SoftBreak:
    location: SourceLocation | None = None
```

### HardBreak

```python
@dataclass(frozen=True, slots=True)
class HardBreak:
    location: SourceLocation | None = None
```

### HtmlInline

```python
@dataclass(frozen=True, slots=True)
class HtmlInline:
    literal: str
    location: SourceLocation | None = None
```

## Type Aliases

```python
Block = Heading | Paragraph | List | ListItem | BlockQuote | CodeBlock | ThematicBreak | HtmlBlock | Directive

Inline = Text | Emphasis | Strong | Code | Link | Image | SoftBreak | HardBreak | HtmlInline
```
