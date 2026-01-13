# Patitas 🐾

**Modern Markdown parser for Python 3.14t** — CommonMark compliant, free-threading ready, 40-50% faster than mistune.

```bash
pip install patitas              # Core parser (zero deps)
pip install patitas[directives]  # + Portable directives (admonition, dropdown, tabs)
pip install patitas[syntax]      # + Syntax highlighting via Rosettes
pip install patitas[bengal]      # Full Bengal directive suite
```

## Why Patitas?

| Feature | Patitas | mistune | markdown-it-py |
|---------|---------|---------|----------------|
| **Performance** | ~40-50% faster | Baseline | ~Similar |
| **Core dependencies** | Zero | Zero | Zero |
| **Free-threading** | Native | No | No |
| **Typed AST** | Frozen dataclasses | `Dict[str, Any]` | `Token` objects |
| **CommonMark** | 0.31.2 (652 examples) | Partial | Full |
| **Built-in plugins** | ✅ Tables, footnotes, math, tasks | Some | Via extensions |
| **Directive syntax** | MyST fenced | RST-style | N/A |

## Quick Start

```python
from patitas import parse, render

# Parse Markdown to AST
doc = parse("# Hello, World!\n\nThis is **Patitas**.")

# Render AST to HTML
html = render(doc)
print(html)
# <h1>Hello, World!</h1>
# <p>This is <strong>Patitas</strong>.</p>
```

### Using the Markdown Class

```python
from patitas import Markdown

md = Markdown()

# Parse and render in one call
html = md("# Hello\n\nParagraph with *emphasis*.")

# Access the AST
doc = md.parse("# Heading")
print(doc.children[0])  # Heading node
```

### Enable Plugins

```python
from patitas import Markdown
from patitas.plugins import tables, footnotes, math, strikethrough, task_lists

md = Markdown(plugins=[tables, footnotes, math, strikethrough, task_lists])

html = md("""
| Header | Header |
|--------|--------|
| Cell   | Cell   |

- [x] Task complete
- [ ] Task pending

Here is math: $E = mc^2$
""")
```

## Features

### CommonMark Compliant

Patitas passes the full CommonMark 0.31.2 specification (652 test cases):

```python
# All standard Markdown works as expected
text = """
# Heading

Paragraph with **bold**, *italic*, and `code`.

- List item
- Another item

> Blockquote

    Code block
"""
```

### Typed AST

All AST nodes are immutable frozen dataclasses with slots:

```python
from patitas import parse
from patitas.nodes import Heading, Paragraph, Strong

doc = parse("# Hello **World**")
heading = doc.children[0]

assert isinstance(heading, Heading)
assert heading.level == 1
assert isinstance(heading.children[0].children[0], Strong)
```

### Zero-Copy Lexer

The lexer stores source offsets, not content copies. This enables:

- Memory-efficient parsing of large documents
- Source mapping for error reporting
- Fast incremental updates

### O(n) Guaranteed

No regex backtracking, no ReDoS vulnerabilities:

```python
# This parses in linear time, even with pathological input
doc = parse("*" * 10000 + "emphasis" + "*" * 10000)
```

### Free-Threading Ready

Designed for Python 3.14t with zero shared mutable state:

```python
from concurrent.futures import ThreadPoolExecutor
from patitas import parse

documents = ["# Doc " + str(i) for i in range(1000)]

with ThreadPoolExecutor() as executor:
    # Safe to parse in parallel
    results = list(executor.map(parse, documents))
```

## Directives (Optional)

Install with `pip install patitas[directives]` for MyST-style directives:

```markdown
:::{note}
This is a note admonition.
:::

:::{warning}
This is a warning.
:::

:::{dropdown} Click to expand
Hidden content here.
:::
```

```python
from patitas import Markdown
from patitas.directives import enable_directives

md = Markdown()
enable_directives(md)

html = md("""
:::{note}
Important information here.
:::
""")
```

## Syntax Highlighting (Optional)

Install with `pip install patitas[syntax]` for code highlighting via Rosettes:

```python
from patitas import Markdown
from patitas.renderers import HtmlRenderer

md = Markdown(renderer=HtmlRenderer(highlight=True))

html = md("""
```python
def hello():
    print("Highlighted!")
```
""")
```

## Roles

Roles provide inline semantic markup:

```markdown
{emphasis}`emphasized text`
{strong}`strong text`
{abbr}`HTML (HyperText Markup Language)`
```

## Architecture

```
Markdown Source → Lexer → Tokens → Parser → Typed AST → Renderer → HTML
```

**Key design principles:**

1. **Zero-Copy Lexer Handoff (ZCLH)**: AST nodes store source offsets, not content copies
2. **Immutable AST**: All nodes are frozen dataclasses with slots
3. **Single-pass rendering**: TOC extraction during render, no post-processing

## The Bengal Cat Family

Patitas is part of the Bengal ecosystem:

```
Bengal — Static site generator (the breed)
├── Kida — Template engine (the cat's name)
├── Rosettes — Syntax highlighter (the spots)
└── Patitas — Markdown parser (the paws) ← You are here
```

## Performance

Benchmarks against mistune 3.0 on CommonMark corpus:

| Metric | Patitas | mistune |
|--------|---------|---------|
| Parse time | ~40-50% faster | Baseline |
| Memory | Lower (zero-copy) | Standard |
| Cold start | <50ms | ~Similar |

## License

MIT License. See [LICENSE](LICENSE) for details.

## Contributing

Contributions welcome! Please read our contributing guidelines.

## Links

- [Documentation](https://github.com/lbliii/patitas)
- [Changelog](CHANGELOG.md)
- [Bengal SSG](https://github.com/lbliii/bengal)
- [Rosettes Highlighter](https://github.com/lbliii/rosettes)
- [Kida Templates](https://github.com/lbliii/kida)
