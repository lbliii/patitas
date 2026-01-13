---
title: API Reference
description: Functions, classes, and modules
draft: false
weight: 10
lang: en
type: doc
tags:
- api
- reference
keywords:
- api
- parse
- render
- markdown
category: reference
icon: code
---

# API Reference

Core API for parsing and rendering Markdown.

## High-Level API

### parse()

Parse Markdown source into a typed AST.

```python
def parse(source: str, *, source_file: str | None = None) -> Sequence[Block]
```

**Parameters:**
- `source`: Markdown source text
- `source_file`: Optional source file path for error messages

**Returns:** Sequence of Block nodes

**Example:**

```python
from patitas import parse

doc = parse("# Hello **World**")
print(doc[0])  # Heading(level=1, ...)
```

### render()

Render a Patitas AST to HTML.

```python
def render(doc: Sequence[Block], *, source: str = "") -> str
```

**Parameters:**
- `doc`: The AST as a sequence of Block nodes
- `source`: Original Markdown source for zero-copy extraction

**Returns:** Rendered HTML string

**Example:**

```python
from patitas import parse, render

doc = parse("# Hello")
html = render(doc, source="# Hello")
print(html)  # <h1>Hello</h1>
```

### Markdown

High-level processor combining parsing and rendering.

```python
class Markdown:
    def __init__(
        self,
        *,
        highlight: bool = False,
        plugins: list[str] | None = None,
    ) -> None: ...

    def __call__(self, source: str, *, source_file: str | None = None) -> str: ...
    def parse(self, source: str, *, source_file: str | None = None) -> Sequence[Block]: ...
    def render(self, doc: Sequence[Block], *, source: str = "") -> str: ...
```

**Example:**

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
print(html)  # <h1>Hello <strong>World</strong></h1>
```

## Low-Level API

### Parser

The Markdown parser.

```python
from patitas.parser import Parser

parser = Parser(source, source_file="example.md")
doc = parser.parse()
```

### Lexer

The state-machine lexer.

```python
from patitas.lexer import Lexer

lexer = Lexer(source)
tokens = list(lexer)
```

### HtmlRenderer

The HTML renderer.

```python
from patitas.renderers.html import HtmlRenderer

renderer = HtmlRenderer(source=source)
html = renderer.render(doc)
```

## Extension Points

### set_highlighter()

Set the global syntax highlighter.

```python
from patitas.highlighting import set_highlighter, Highlighter

class MyHighlighter:
    def highlight(self, code: str, lang: str) -> str:
        return f"<pre><code class='{lang}'>{code}</code></pre>"

set_highlighter(MyHighlighter())
```

### set_icon_resolver()

Set the global icon resolver.

```python
from patitas.icons import set_icon_resolver, IconResolver

class MyIcons:
    def resolve(self, name: str) -> str | None:
        return f"<span class='icon-{name}'></span>"

set_icon_resolver(MyIcons())
```
