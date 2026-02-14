# ฅᨐฅ Patitas

[![PyPI version](https://img.shields.io/pypi/v/patitas.svg)](https://pypi.org/project/patitas/)
[![Build Status](https://github.com/lbliii/patitas/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/patitas/actions/workflows/tests.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://pypi.org/project/patitas/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CommonMark](https://img.shields.io/badge/CommonMark-0.31.2-brightgreen.svg)](https://spec.commonmark.org/0.31.2/)
[![ReDoS Safe](https://img.shields.io/badge/ReDoS-Safe-brightgreen.svg)](docs/security.md)

**The secure, typed Markdown parser for modern Python.**

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
```

---

## Why Patitas?

|   | Patitas | mistune | markdown-it-py |
|---|---------|---------|----------------|
| **ReDoS-proof** | ✅ O(n) FSM lexer | ❌ Regex-based | ✅ Token-based |
| **CommonMark** | 0.31.2 ✅ | Partial | 0.31.2 ✅ |
| **Free-threading** | ✅ Python 3.14t safe | ✅ Works | ❌ **Crashes** |
| **Typed AST** | ✅ Frozen dataclasses | ❌ `Dict[str, Any]` | ❌ Token objects |
| **Dependencies** | Zero | Zero | Zero |
| **Directives** | ✅ MyST syntax | RST-style | Plugin required |

**Patitas is the only CommonMark-compliant parser with typed AST that works safely under Python 3.14t free-threading.**

---

## Installation

```bash
pip install patitas
```

Requires Python 3.14+

**Optional extras:**

```bash
pip install patitas[syntax]      # Syntax highlighting via Rosettes
pip install patitas[all]         # All optional features
```

---

## Quick Start

| Function | Description |
|----------|-------------|
| `parse(source)` | Parse Markdown to typed AST |
| `parse_notebook(content, source_path?)` | Parse Jupyter .ipynb to (markdown, metadata) |
| `parse_incremental(new, prev, ...)` | Re-parse only the changed region (O(change)) |
| `render(doc)` | Render AST to HTML |
| `Markdown()` | All-in-one parser and renderer |

### Notebook support

Parse Jupyter notebooks (.ipynb) to Markdown content and metadata — zero dependencies, stdlib JSON only:

```python
from patitas import parse_notebook

with open("demo.ipynb") as f:
    content, metadata = parse_notebook(f.read(), "demo.ipynb")

# content: Markdown string (cells → fenced code, outputs → HTML)
# metadata: title, type, notebook{kernel_name, cell_count}, etc.
```

---

## Security

**Patitas is immune to ReDoS attacks.**

Traditional Markdown parsers use regex patterns vulnerable to catastrophic backtracking:

```python
# Malicious input that can freeze regex-based parsers
evil = "a](" + "\\)" * 10000

# mistune: hangs for seconds/minutes
# Patitas: completes in milliseconds (O(n) guaranteed)
```

Patitas uses a hand-written finite state machine lexer:
- **Single character lookahead** — No backtracking, ever
- **Linear time guaranteed** — Processing time scales with input length
- **Safe for untrusted input** — Use in web apps, APIs, user-facing tools

[Learn more about Patitas security →](docs/security.md)

---

## Performance

**Python 3.14t (free-threading) — 652 CommonMark examples:**

| Parser | Single Thread | 4 Threads | Thread-safe? |
|--------|---------------|-----------|--------------|
| mistune | 11ms | 4ms | ✅ |
| **Patitas** | 17ms | 7ms | ✅ |
| markdown-it-py | 20ms | **CRASH** | ❌ |

```bash
# Run benchmarks yourself
PYTHONPATH=src python3.14t benchmarks/benchmark_vs_mistune.py
```

**Key insights:**
- **mistune is faster** — regex engines are highly optimized
- **Patitas scales linearly** — 2.5x speedup with 4 threads
- **markdown-it-py crashes** under free-threading (race condition in URL encoding)

Patitas prioritizes **safety over raw speed**: O(n) guaranteed parsing, typed AST, and full thread-safety.

---

## Features

| Feature | Description |
|---------|-------------|
| **CommonMark** | Full 0.31.2 spec compliance (652 examples) |
| **Typed AST** | Immutable frozen dataclasses with slots |
| **Plugins** | Tables, footnotes, math, strikethrough, task lists |
| **Directives** | MyST-style blocks (admonition, dropdown, tabs) |
| **Roles** | Inline semantic markup |
| **Incremental** | Re-parse only changed blocks — O(change) not O(document) |
| **Thread-safe** | Zero shared mutable state, free-threading ready |

---

## Usage

<details>
<summary><strong>Basic Parsing</strong></summary>

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
<summary><strong>Typed AST</strong> — IDE autocomplete, catch errors at dev time</summary>

```python
from patitas import parse
from patitas.nodes import Heading, Paragraph, Strong

doc = parse("# Hello **World**")
heading = doc.children[0]

# Full type safety
assert isinstance(heading, Heading)
assert heading.level == 1

# IDE knows the types!
for child in heading.children:
    if isinstance(child, Strong):
        print(f"Bold text: {child.children}")
```

All nodes are `@dataclass(frozen=True, slots=True)` — immutable and memory-efficient.

</details>

<details>
<summary><strong>Directives</strong> — MyST-style blocks</summary>

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
<summary><strong>Custom Directives</strong> — Extend with your own</summary>

```python
from patitas import Markdown, create_registry_with_defaults

# Define a custom directive
class AlertDirective:
    names = ("alert",)
    token_type = "alert"
    
    def render(self, directive, renderer):
        return f'<div class="alert">{directive.title}</div>'

# Extend defaults with your directive
builder = create_registry_with_defaults()  # Has admonition, dropdown, tabs
builder.register(AlertDirective())

# Use it
md = Markdown(directive_registry=builder.build())
html = md(":::{alert} This is important!\n:::")
```

</details>

<details>
<summary><strong>Syntax Highlighting</strong></summary>

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

Uses [Rosettes](https://github.com/lbliii/rosettes) for O(n) highlighting.

</details>

<details>
<summary><strong>Free-Threading</strong> — Python 3.14t</summary>

```python
from concurrent.futures import ThreadPoolExecutor
from patitas import parse

documents = ["# Doc " + str(i) for i in range(1000)]

with ThreadPoolExecutor() as executor:
    # Safe to parse in parallel — no shared mutable state
    results = list(executor.map(parse, documents))
```

Patitas is designed for Python 3.14t's free-threading mode (PEP 703).

</details>

---

## Migrate from mistune

```python
# Before (mistune)
import mistune
md = mistune.create_markdown()
html = md(source)

# After (patitas) — same API!
from patitas import Markdown
md = Markdown()
html = md(source)
```

**Key differences:**
- Patitas uses MyST directive syntax (`:::{note}`) vs mistune's RST (`.. note::`)
- Patitas AST is typed dataclasses vs mistune's `Dict[str, Any]`
- Patitas is ReDoS-proof; mistune uses regex

[Full migration guide →](docs/migrate-from-mistune.md)

---

## The Bengal Ecosystem

A structured reactive stack — every layer written in pure Python for 3.14t free-threading.

| | | | |
|--:|---|---|---|
| **ᓚᘏᗢ** | [Bengal](https://github.com/lbliii/bengal) | Static site generator | [Docs](https://lbliii.github.io/bengal/) |
| **∿∿** | [Purr](https://github.com/lbliii/purr) | Content runtime | — |
| **⌁⌁** | [Chirp](https://github.com/lbliii/chirp) | Web framework | [Docs](https://lbliii.github.io/chirp/) |
| **=^..^=** | [Pounce](https://github.com/lbliii/pounce) | ASGI server | [Docs](https://lbliii.github.io/pounce/) |
| **)彡** | [Kida](https://github.com/lbliii/kida) | Template engine | [Docs](https://lbliii.github.io/kida/) |
| **ฅᨐฅ** | **Patitas** | Markdown parser ← You are here | [Docs](https://lbliii.github.io/patitas/) |
| **⌾⌾⌾** | [Rosettes](https://github.com/lbliii/rosettes) | Syntax highlighter | [Docs](https://lbliii.github.io/rosettes/) |

Python-native. Free-threading ready. No npm required.

---

## Development

```bash
git clone https://github.com/lbliii/patitas.git
cd patitas
uv sync --group dev
pytest
```

**Run benchmarks:**

```bash
pip install mistune markdown-it-py
python benchmarks/benchmark_vs_mistune.py
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
