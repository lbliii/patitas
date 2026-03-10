# ฅᨐฅ Patitas

[![PyPI version](https://img.shields.io/pypi/v/patitas.svg)](https://pypi.org/project/patitas/)
[![Build Status](https://github.com/lbliii/patitas/actions/workflows/tests.yml/badge.svg)](https://github.com/lbliii/patitas/actions/workflows/tests.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://pypi.org/project/patitas/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![CommonMark](https://img.shields.io/badge/CommonMark-0.31.2-brightgreen.svg)](https://spec.commonmark.org/0.31.2/)
[![ReDoS Safe](https://img.shields.io/badge/ReDoS-Safe-brightgreen.svg)](docs/security.md)

**A Python Markdown parser and CommonMark parser for typed ASTs, frontmatter, directives, and notebook content.**

```python
from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
```

---

## What is Patitas?

Patitas is a pure-Python Markdown parser that parses to a typed AST and renders to
HTML. It's CommonMark 0.31.2 compliant, has zero runtime dependencies, and is built
for Python 3.14+.

**Why people pick it:**

- **ReDoS-proof** — O(n) finite state machine lexer, no regex backtracking. Safe for untrusted input in web apps and APIs.
- **Typed AST** — Frozen dataclasses (`Heading`, `Paragraph`, `Strong`, etc.) with IDE autocomplete and type checking.
- **CommonMark** — Full 0.31.2 spec compliance (652 examples).
- **Incremental parsing** — Re-parse only changed blocks; ~200x faster for small edits than full re-parse.
- **Free-threading native** — Frozen AST, `ContextVar` config, no shared mutable state. 1,000 documents parse in parallel with near-linear thread scaling on 3.14t — no locks, no special API.
- **LLM-safe** — `render_llm` + composable `sanitize` policies for RAG, retrieval, safe context.
- **Directives** — MyST-style blocks (admonition, dropdown, tabs) plus custom directives.
- **Notebook + frontmatter support** — Parse `.ipynb` content and YAML frontmatter as part of content pipelines.

## Use Patitas For

- **Markdown to HTML pipelines** — Render docs, blogs, and site content from Python
- **Typed Markdown processing** — Analyze or transform documents through a typed AST
- **Secure user-input parsing** — Handle untrusted Markdown without regex backtracking risk
- **Content tooling** — Frontmatter extraction, excerpts, meta descriptions, and notebook conversion
- **Modern docs stacks** — Directives, syntax highlighting, LLM-safe rendering, and incremental parsing

---

## What it does

| Function | Description |
|----------|-------------|
| `parse(source)` | Parse Markdown to typed AST |
| `parse_frontmatter(content)` | Parse YAML frontmatter to (metadata, body) |
| `parse_notebook(content, source_path?)` | Parse Jupyter .ipynb to (markdown, metadata) |
| `parse_incremental(new, prev, ...)` | Re-parse only the changed region (O(change)) |
| `render(doc)` | Render AST to HTML |
| `render_llm(doc)` | Render AST to LLM-friendly plain text (no HTML) |
| `sanitize(doc, policy)` | Strip HTML, dangerous URLs, zero-width chars |
| `extract_text(node)` | Extract plain text from any AST node |
| `extract_excerpt(ast, source, ...)` | Structurally correct excerpt from AST (list previews, meta) |
| `extract_meta_description(ast, source)` | Meta description from first paragraph/heading |
| `extract_body(content)` | Strip --- delimited frontmatter block (no YAML parse) |
| `Markdown()` | All-in-one parser and renderer |

---

## More Features

- **ReDoS-proof** — O(n) finite state machine lexer, no regex backtracking. Safe for untrusted input in web apps and APIs.
- **Typed AST** — Frozen dataclasses (`Heading`, `Paragraph`, `Strong`, etc.) with IDE autocomplete and type checking.
- **CommonMark** — Full 0.31.2 spec compliance (652 examples).
- **Incremental parsing** — Re-parse only changed blocks; ~200x faster for small edits than full re-parse.
- **Free-threading native** — Frozen AST, `ContextVar` config, no shared mutable state. 1,000 documents parse in parallel with near-linear thread scaling on 3.14t — no locks, no special API.
- **LLM-safe** — `render_llm` + composable `sanitize` policies for RAG, retrieval, safe context.
- **Directives** — MyST-style blocks (admonition, dropdown, tabs) plus custom directives.
- **Plugins** — Tables, footnotes, math, strikethrough, task lists.
- **Minimal dependencies** — PyYAML for frontmatter; core parser is pure Python.

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

### Parse and render

```python
from patitas import parse, render

doc = parse("# Hello **World**")
html = render(doc)
# <h1 id="hello-world">Hello <strong>World</strong></h1>
```

### Frontmatter

Parse YAML frontmatter from Markdown or other content, returning a `(metadata, body)` tuple:

```python
from patitas import parse_frontmatter, extract_body

content = """---
title: Hello
weight: 10
---
# Body content
"""
metadata, body = parse_frontmatter(content)
# metadata: {"title": "Hello", "weight": 10.0}
# body: "# Body content"

# When YAML is broken, extract_body strips the --- block without parsing
body_only = extract_body(content)
```

### Notebook support

Parse Jupyter notebooks (.ipynb) to Markdown content and metadata — stdlib JSON only:

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

# Patitas: completes in milliseconds (O(n) guaranteed)
```

Patitas uses a hand-written finite state machine lexer:
- **Single character lookahead** — No backtracking, ever
- **Linear time guaranteed** — Processing time scales with input length
- **Safe for untrusted input** — Use in web apps, APIs, user-facing tools

[Learn more about Patitas security →](docs/security.md)

---

## Performance

- **652 CommonMark examples** — ~26ms single-threaded
- **Incremental parsing** — For a 1-char edit in a ~100KB doc, `parse_incremental` is ~200x faster than full re-parse (~160µs vs ~32ms)
- **Parallel scaling** — Near-linear thread scaling under Python 3.14t free-threading. Run `python benchmarks/benchmark_parallel.py` to see results on your machine. Example on 8-core:

  ```
    Threads    Time      Speedup
    1          1.52s     1.00x
    2          0.79s     1.92x
    4          0.41s     3.71x
    8          0.23s     6.61x
  ```

```bash
# From repo (after uv sync --group dev):
python benchmarks/benchmark_vs_mistune.py
python benchmarks/benchmark_parallel.py   # Free-threading scaling
pytest benchmarks/benchmark_vs_mistune.py benchmarks/benchmark_incremental.py benchmarks/benchmark_directives.py benchmarks/benchmark_scaling.py benchmarks/benchmark_excerpt.py -v --benchmark-only --benchmark-group-by=group
```

See [benchmarks/README.md](benchmarks/README.md) for the full suite (pipelines, phase-breakdown, CI threshold checks).

---

## Usage

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
from patitas.directives.decorator import directive

# Define a custom directive with the @directive decorator
@directive("alert")
def render_alert(node, children: str, sb) -> None:
    sb.append(f'<div class="alert">{children}</div>')

# Extend defaults with your directive
builder = create_registry_with_defaults()  # Has admonition, dropdown, tabs
builder.register(render_alert())

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

<details>
<summary><strong>LLM Safety</strong> — Sanitize and render for RAG, retrieval</summary>

When sending Markdown to an LLM, sanitize untrusted content and render to plain text:

```python
from patitas import parse, sanitize, render_llm
from patitas.sanitize import llm_safe

doc = parse(user_content)
clean = sanitize(doc, policy=llm_safe)  # Strip HTML, dangerous URLs, zero-width chars
safe_text = render_llm(clean, source=user_content)
```

Pre-built policies: `llm_safe`, `web_safe` (alias), `strict`. Compose with `|`.

</details>

---

## Migrate from mistune

Same API — swap the import:

```python
from patitas import Markdown
md = Markdown()
html = md(source)
```

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

**Run benchmarks** (after `uv sync --group dev`):

```bash
python benchmarks/benchmark_vs_mistune.py
python benchmarks/benchmark_parallel.py   # Free-threading scaling demo
pytest benchmarks/benchmark_*.py -v --benchmark-only --benchmark-group-by=group   # Full suite
```

---

## License

MIT License — see [LICENSE](LICENSE) for details.
