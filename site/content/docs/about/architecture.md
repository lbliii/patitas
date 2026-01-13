---
title: Architecture
description: How the lexer, parser, and renderer work
draft: false
weight: 10
lang: en
type: doc
tags:
- architecture
- design
keywords:
- lexer
- parser
- renderer
- ast
category: explanation
icon: cpu
---

# Architecture

Patitas uses a three-stage pipeline: Lexer → Parser → Renderer.

## Overview

```
Source Text → Lexer → Tokens → Parser → AST → Renderer → HTML
```

## Lexer

The lexer is a state-machine tokenizer. No regex.

**Key features:**
- O(n) guaranteed time complexity
- No backtracking
- No ReDoS vulnerabilities
- Single-pass scanning

**Token types:**
- Block boundaries (paragraphs, headings, lists)
- Inline markers (emphasis, links, code)
- Literals (text, code content)

```python
from patitas.lexer import Lexer

lexer = Lexer("# Hello **World**")
for token in lexer:
    print(token.type, token.value)
```

## Parser

The parser consumes tokens to build the AST.

**Key features:**
- Recursive descent parsing
- Immediate AST construction
- No intermediate representations
- Frozen dataclass nodes

**Parsing strategy:**
1. Scan for block structure
2. Parse block content
3. Parse inline elements within blocks
4. Build immutable node tree

```python
from patitas.parser import Parser

parser = Parser("# Hello")
doc = parser.parse()
```

## AST

The Abstract Syntax Tree uses frozen dataclasses with slots.

**Why frozen?**
- Thread-safe by default
- Hashable (can be cached)
- Prevents accidental mutation

**Why slots?**
- Reduced memory footprint
- Faster attribute access

```python
@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    children: tuple[Inline, ...]
    location: SourceLocation | None = None
```

## Renderer

The HTML renderer traverses the AST using pattern matching.

**Key features:**
- StringBuilder for O(n) output
- Zero-copy text extraction where possible
- Pluggable highlighter and icon resolver

```python
from patitas.renderers.html import HtmlRenderer

renderer = HtmlRenderer(source=source_text)
html = renderer.render(doc)
```

## Extension Points

### Highlighter Protocol

```python
class Highlighter(Protocol):
    def highlight(self, code: str, lang: str) -> str: ...
```

### IconResolver Protocol

```python
class IconResolver(Protocol):
    def resolve(self, name: str) -> str | Inline | None: ...
```

### DirectiveHandler Protocol

```python
class DirectiveHandler(Protocol):
    name: str
    def parse(self, ...) -> Block | None: ...
    def render(self, ...) -> None: ...
```
