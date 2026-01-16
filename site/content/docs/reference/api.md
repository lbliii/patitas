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
def parse(
    source: str,
    *,
    source_file: str | None = None,
    directive_registry: DirectiveRegistry | None = None,
) -> Document
```

**Parameters:**
- `source`: Markdown source text
- `source_file`: Optional source file path for error messages
- `directive_registry`: Custom directive registry (uses defaults if None)

**Returns:** Document AST root node

**Example:**

```python
from patitas import parse

doc = parse("# Hello **World**")
print(doc.children[0])  # Heading(level=1, ...)
```

### render()

Render a Patitas AST to HTML.

```python
def render(
    doc: Document,
    *,
    source: str = "",
    highlight: bool = False,
    directive_registry: DirectiveRegistry | None = None,
) -> str
```

**Parameters:**
- `doc`: Document AST to render
- `source`: Original Markdown source for zero-copy extraction
- `highlight`: Enable syntax highlighting for code blocks
- `directive_registry`: Custom directive registry for rendering

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
        directive_registry: DirectiveRegistry | None = None,
    ) -> None: ...

    def __call__(self, source: str) -> str: ...
    def parse(self, source: str, *, source_file: str | None = None) -> Document: ...
    def render(self, doc: Document, *, source: str = "") -> str: ...
```

**Example:**

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
print(html)  # <h1>Hello <strong>World</strong></h1>

# With plugins
md = Markdown(plugins=["table", "math", "strikethrough"])
html = md("| a | b |\n|---|---|\n| 1 | 2 |")
```

## Configuration API

Thread-local configuration for advanced use cases.

### ParseConfig

Immutable configuration dataclass.

```python
from patitas import ParseConfig

config = ParseConfig(
    tables_enabled=True,
    math_enabled=True,
    strikethrough_enabled=False,
    task_lists_enabled=False,
    footnotes_enabled=False,
    autolinks_enabled=False,
    directive_registry=None,
    strict_contracts=False,
    text_transformer=None,
)
```

### parse_config_context()

Context manager for temporary config changes.

```python
from patitas import parse_config_context, ParseConfig, Parser

with parse_config_context(ParseConfig(tables_enabled=True)):
    parser = Parser("| a | b |")
    result = parser.parse()
# Config automatically reset after context
```

### get/set/reset functions

```python
from patitas import get_parse_config, set_parse_config, reset_parse_config

# Get current config
config = get_parse_config()

# Set custom config
set_parse_config(ParseConfig(math_enabled=True))

# Reset to defaults
reset_parse_config()
```

## Low-Level API

### Parser

The Markdown parser. Configuration is read from ContextVar.

```python
from patitas import Parser, parse_config_context, ParseConfig

# Simple usage (uses default config)
parser = Parser(source, source_file="example.md")
doc = parser.parse()

# With custom config
with parse_config_context(ParseConfig(tables_enabled=True)):
    parser = Parser(source)
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
