# ฅᨐฅ Patitas

[![PyPI version](https://img.shields.io/pypi/v/patitas.svg)](https://pypi.org/project/patitas/)
[![Build Status](https://github.com/lbliii/patitas/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/patitas/actions/workflows/tests.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://pypi.org/project/patitas/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

**Modern Markdown parser for Python 3.14t**

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
```

---

## Why Patitas?

- **Fast** — 40-50% faster than mistune, O(n) guaranteed parsing
- **Safe** — No regex backtracking, no ReDoS vulnerabilities
- **Modern** — Python 3.14t free-threading native, fully typed
- **Standards-based** — CommonMark 0.31.2 compliant (652 test cases)
- **Zero dependencies** — Pure Python core, optional extras for features

---

## Installation

```bash
pip install patitas
```

Requires Python 3.14+

**Optional extras:**

```bash
pip install patitas[directives]  # MyST-style directives (admonition, tabs, dropdown)
pip install patitas[syntax]      # Syntax highlighting via Rosettes
pip install patitas[bengal]      # Full Bengal directive suite
pip install patitas[all]         # Everything except Bengal
```

---

## Quick Start

| Function | Description |
|----------|-------------|
| `parse(source)` | Parse Markdown to typed AST |
| `render(doc)` | Render AST to HTML |
| `Markdown()` | All-in-one parser and renderer |

---

## Features

| Feature | Description |
|---------|-------------|
| **CommonMark** | Full 0.31.2 spec compliance (652 examples) |
| **Typed AST** | Immutable frozen dataclasses with slots |
| **Plugins** | Tables, footnotes, math, strikethrough, task lists |
| **Directives** | MyST-style blocks (admonition, dropdown, tabs) |
| **Roles** | Inline semantic markup |
| **Thread-safe** | Zero shared mutable state, free-threading ready |

---

## Usage

<details>
<summary><strong>Basic Parsing</strong> — Parse and render Markdown</summary>

```python
from patitas import parse, render

# Parse to AST
doc = parse("# Hello **World**")

# Render to HTML
html = render(doc)
# <h1 id="hello-world">Hello <strong>World</strong></h1>
```

</details>

<details>
<summary><strong>Markdown Class</strong> — All-in-one interface</summary>

```python
from patitas import Markdown

md = Markdown()

# Parse and render in one call
html = md("# Hello\n\nParagraph with *emphasis*.")

# Access the AST separately
doc = md.parse("# Heading")
print(doc[0])  # Heading(level=1, ...)
```

</details>

<details>
<summary><strong>Plugins</strong> — Enable extensions</summary>

```python
from patitas import Markdown

md = Markdown(plugins=["table", "footnotes", "math", "strikethrough", "task_lists"])

html = md("""
| Header | Header |
|--------|--------|
| Cell   | Cell   |

- [x] Task complete
- [ ] Task pending

Here is math: $E = mc^2$
""")
```

</details>

<details>
<summary><strong>Typed AST</strong> — Work with structured nodes</summary>

```python
from patitas import parse
from patitas.nodes import Heading, Paragraph, Strong

doc = parse("# Hello **World**")
heading = doc[0]

assert isinstance(heading, Heading)
assert heading.level == 1
assert isinstance(heading.children[0].children[0], Strong)
```

All nodes are frozen dataclasses with slots — immutable and memory-efficient.

</details>

<details>
<summary><strong>Directives</strong> — MyST-style blocks</summary>

With `pip install patitas[directives]`:

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

:::{tab-set}

:::{tab-item} Python
Python code here.
:::

:::{tab-item} JavaScript
JavaScript code here.
:::

:::
```

</details>

<details>
<summary><strong>Syntax Highlighting</strong> — Code block highlighting</summary>

With `pip install patitas[syntax]`:

```python
from patitas import Markdown

md = Markdown(highlight=True)

html = md("""
```python
def hello():
    print("Highlighted!")
```
""")
```

Uses Rosettes for O(n) highlighting with 55+ language support.

</details>

<details>
<summary><strong>Free-Threading</strong> — Parallel parsing</summary>

```python
from concurrent.futures import ThreadPoolExecutor
from patitas import parse

documents = ["# Doc " + str(i) for i in range(1000)]

with ThreadPoolExecutor() as executor:
    # Safe to parse in parallel — no shared mutable state
    results = list(executor.map(parse, documents))
```

</details>

---

## Comparison

| Feature | Patitas | mistune | markdown-it-py |
|---------|---------|---------|----------------|
| **Performance** | ~40-50% faster | Baseline | ~Similar |
| **Dependencies** | Zero | Zero | Zero |
| **Free-threading** | Native | No | No |
| **AST** | Frozen dataclasses | `Dict[str, Any]` | `Token` objects |
| **CommonMark** | 0.31.2 ✅ | Partial | 0.31.2 ✅ |
| **ReDoS safe** | ✅ O(n) guaranteed | Regex-based | Regex-based |
| **Directives** | MyST fenced | RST-style | N/A |

---

## Architecture

<details>
<summary><strong>Parsing Pipeline</strong> — Source to HTML</summary>

```
Markdown Source → Lexer → Tokens → Parser → Typed AST → Renderer → HTML
```

**Key design principles:**
- **Zero-Copy Lexer**: AST nodes store source offsets, not content copies
- **Immutable AST**: All nodes are frozen dataclasses with slots
- **Single-pass rendering**: TOC extraction during render, no post-processing

</details>

<details>
<summary><strong>State Machine Lexer</strong> — O(n) guaranteed</summary>

The lexer is a hand-written finite state machine:
- Single character lookahead
- No backtracking (no ReDoS possible)
- Immutable state (thread-safe)
- Local variables only (no shared mutable state)

</details>

<details>
<summary><strong>Thread Safety</strong> — Free-threading ready</summary>

All public APIs are thread-safe by design:
- **Parsing** — Uses only local state
- **Rendering** — StringBuilder pattern, no shared state
- **AST nodes** — Immutable frozen dataclasses
- Module declares itself GIL-independent (PEP 703)

</details>

---

## Performance

Benchmarked against mistune 3.0 on CommonMark corpus:

| Metric | Patitas | mistune | Improvement |
|--------|---------|---------|-------------|
| Parse time | 12ms | 20ms | **40% faster** |
| Memory | Lower | Standard | Zero-copy lexer |
| Cold start | <50ms | ~Similar | — |

---

## The Bengal Cat Family

Patitas is part of the Bengal ecosystem:

```
ᓚᘏᗢ  Bengal    — Static site generator (the breed)
 )彡  Kida      — Template engine (the cat's name)
⌾⌾⌾  Rosettes  — Syntax highlighter (the spots)
ฅᨐฅ  Patitas   — Markdown parser (the paws) ← You are here
```

---

## Development

```bash
git clone https://github.com/lbliii/patitas.git
cd patitas
uv sync --group dev
pytest
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
