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
- parse_notebook
- render
- markdown
- serialization
- to_dict
- from_dict
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

### parse_notebook()

Parse a Jupyter notebook (`.ipynb`) to Markdown content and metadata. Zero dependencies — uses stdlib `json` only. Supports nbformat 4 and 5.

```python
def parse_notebook(
    content: str,
    source_path: Path | str | None = None,
) -> tuple[str, dict[str, Any]]
```

**Parameters:**
- `content`: Raw JSON content of the `.ipynb` file (caller handles I/O)
- `source_path`: Optional path for title fallback when notebook has no title

**Returns:** Tuple of `(markdown_content, metadata_dict)`

- `markdown_content`: Markdown string — markdown cells as-is, code cells as fenced blocks, outputs as HTML
- `metadata`: Dict with `title`, `type: "notebook"`, `notebook.kernel_name`, `notebook.cell_count`, etc.

**Raises:**
- `json.JSONDecodeError`: If content is not valid JSON
- `ValueError`: If nbformat is 3 or older

**Example:**

```python
from patitas import parse_notebook

with open("demo.ipynb") as f:
    content, metadata = parse_notebook(f.read(), "demo.ipynb")

# content: Markdown string ready for parse() or render
# metadata: title, type, notebook{kernel_name, cell_count}, etc.
print(metadata["notebook"]["kernel_name"])  # e.g. "python3"
```

Used by [Bengal](https://github.com/lbliii/bengal) for native notebook rendering — drop `.ipynb` into content and build.

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

## Serialization API

Convert AST nodes to/from JSON-compatible dicts and strings. Deterministic output
for cache-key stability. Useful for caching parsed ASTs (Bengal incremental builds)
and sending ASTs over the wire (Purr SSE).

### to_dict() / from_dict()

In-memory dict format — use for caching or when you need to inspect or modify
the structure before serializing to JSON.

```python
from patitas import parse, to_dict, from_dict

doc = parse("# Hello **World**")
data = to_dict(doc)
restored = from_dict(data)
assert doc == restored
```

**to_dict(node: Node) -> dict[str, Any]**

- `node`: Any AST node (Document, Heading, Paragraph, etc.)
- **Returns:** JSON-compatible dict with `_type` discriminator

**from_dict(data: dict[str, Any]) -> Node**

- `data`: Dict produced by `to_dict`
- **Returns:** Reconstructed typed AST node

### to_json() / from_json()

JSON string format — use for persistence, wire transfer, or human inspection.

```python
from patitas import parse, to_json, from_json

doc = parse("# Hello **World**")
json_str = to_json(doc)
restored = from_json(json_str)
assert doc == restored
```

**to_json(doc: Document, *, indent: int | None = None) -> str**

- `doc`: Document AST root
- `indent`: Optional indent for pretty-printing (None = compact)

**from_json(data: str) -> Document**

- `data`: JSON string from `to_json`
- **Returns:** Reconstructed Document

See [Serialization](/docs/extending/serialization/) for caching and wire-transfer patterns.

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

### ParseConfig.from_dict()

Create a `ParseConfig` from a dictionary. Unknown keys are silently ignored,
making this safe for framework integration where config may come from YAML
files or external sources.

```python
from patitas import ParseConfig

config = ParseConfig.from_dict({
    "tables_enabled": True,
    "math_enabled": True,
    "unknown_key": "silently ignored",
})
# config.tables_enabled == True
# config.math_enabled == True
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
