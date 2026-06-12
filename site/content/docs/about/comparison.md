---
title: Parser Comparison
description: An honest comparison of Patitas vs markdown-it-py, Python-Markdown, and mistune
draft: false
weight: 40
lang: en
type: doc
tags:
- about
- comparison
keywords:
- comparison
- markdown-it-py
- python-markdown
- mistune
- python markdown parser
- free-threading
- typed ast
category: explanation
icon: table
---

# Parser Comparison

Choosing a Python Markdown parser is a tradeoff. This page compares Patitas with
the three most common alternatives — [markdown-it-py][mdit], [Python-Markdown][pymd],
and [mistune][mistune] — so you can decide which fits your project.

The goal here is to be honest, not to win every row. Patitas explicitly does
**not** try to beat mistune or markdown-it-py on raw single-thread speed (see
[Explicitly Not Planned](#a-note-on-honesty) below). It optimizes for safety,
typing, and free-threading instead.

## At a Glance

| Dimension | Patitas | markdown-it-py | Python-Markdown | mistune |
|---|---|---|---|---|
| Implementation | Pure Python, hand-written FSM lexer | Pure Python (port of markdown-it) | Pure Python | Pure Python |
| Python version | 3.14+ only | 3.8+ | 3.8+ | 3.8+ |
| Free-threading (3.14t) | Designed for it: frozen AST, `ContextVar` config | Not designed for it | Not designed for it | Not designed for it |
| CommonMark | Yes — targets 0.31.2 | Yes — CommonMark compliant | No (its own dialect) | Partial / dialect |
| GFM-style features | Opt-in plugins (~97% of GFM 0.29 spec measured) | Via `mdit_py_plugins` | Via extensions | Via plugins |
| AST model | Typed, immutable dataclass tree | Flat `Token` stream | ElementTree | Nested dicts |
| Extensibility | Directives, roles, plugins, custom renderers | Rules + plugins (mutating instance) | Extensions / treeprocessors | Plugins + renderers |
| MyST directives | Native (`:::{name}`) | Via MyST/`mdit_py_plugins` | Limited | RST-style only |
| Output sanitization | AST-level `sanitize()` with policies | `html: False` default | `safe_mode` removed; use bleach | `escape=True` default |
| Incremental re-parse | `parse_incremental()` | No | No | No |
| Single-thread speed | Competitive, not the focus | Fast | Slower | Fastest |

The percentages and pass counts above are tracked in the repo (see
[GFM compliance tracking](https://github.com/lbliii/patitas/blob/main/docs/gfm-compliance.md))
rather than asserted as marketing claims.

## Python Version and Free-Threading

This is the sharpest line between Patitas and everything else.

- **Patitas is Python 3.14+ only.** Supporting older versions would compromise
  the free-threading and modern-syntax design, so it is
  [explicitly not planned](#a-note-on-honesty).
- AST nodes are frozen, slotted dataclasses, and parser/renderer configuration
  is held in a `ContextVar` rather than on shared mutable instance state. A
  single `Markdown` instance is safe to reuse across free-threaded (3.14t)
  workers, and `Markdown.parse_many(...)` exists for batch workloads.
- markdown-it-py, Python-Markdown, and mistune all predate free-threading and
  configure a mutable parser instance, so they are not designed to be shared
  across no-GIL threads.

See [Thread Safety](./thread-safety) for the full design.

## Standards Compliance

- **Patitas** targets **CommonMark 0.31.2** and additionally measures **GFM 0.29**
  compliance with the GFM plugins enabled. Both pass rates are tracked as
  ratchets in the test suite so they cannot silently regress.
- **markdown-it-py** is CommonMark compliant by design (it is a port of the
  reference JavaScript `markdown-it`).
- **Python-Markdown** implements its own historical dialect, not CommonMark.
- **mistune** is fast and popular but follows its own dialect rather than the
  full CommonMark spec.

## Typed AST vs Tokens vs Trees

Each parser exposes its parse result differently:

- **Patitas** — a typed, immutable tree of dataclasses (`Document`, `Heading`,
  `Paragraph`, ...). You get `isinstance` narrowing, IDE autocomplete, and
  compile-time type checking, plus `to_dict()` / `to_json()` serialization and
  `BaseVisitor` / `transform` for traversal.
- **markdown-it-py** — a flat list of `Token` objects walked with
  `nesting`/`type` bookkeeping.
- **Python-Markdown** — an `xml.etree.ElementTree`, manipulated with
  treeprocessors.
- **mistune** — nested `dict[str, Any]` structures.

If your pipeline does AST analysis or transformation (linting, link rewriting,
excerpts, LLM preprocessing), the typed tree is the main reason to pick Patitas.

## Extensibility

| | Patitas | markdown-it-py | Python-Markdown | mistune |
|---|---|---|---|---|
| Block extensions | Directives (`:::{name}`) + plugins | Block rules + plugins | Block processors | Plugins |
| Inline extensions | Roles + plugins | Inline rules + plugins | Inline patterns | Plugins |
| Custom output | Subclass `HtmlRenderer` / custom registry | Renderer rules / subclass | Subclass `Treeprocessor` / serializer | Subclass renderer |
| Statefulness | Stateless registries, immutable config | Mutating one instance | Registered on a `Markdown` instance | Plugin functions |

Patitas extension handlers are required to be stateless and registry-driven,
which is what keeps a configured `Markdown` instance safe to share across
threads.

## Security

The default renderers of Patitas, markdown-it-py (`html: True`), and mistune
(`escape=False`) are all CommonMark-style: raw HTML and `javascript:`/`data:`
URLs pass through. Patitas does not silently strip them — instead it offers an
AST-level `sanitize()` step with policies (for example `web_safe`) that you
apply before rendering untrusted input:

```python
from patitas import parse, sanitize, render
from patitas.sanitize import web_safe

doc = parse(untrusted_source)
html = render(sanitize(doc, policy=web_safe))
```

Patitas's lexer is also hand-written and runs in guaranteed O(n) with no regex
backtracking, which removes a class of ReDoS risks that regex-driven parsers can
carry. See [Security](https://github.com/lbliii/patitas/blob/main/docs/security.md).

## Migration Effort

| From | Effort | Guide |
|---|---|---|
| markdown-it-py | Low for rendering; medium if you walk tokens (move to the typed AST) | [Migrate from markdown-it-py](https://github.com/lbliii/patitas/blob/main/docs/migrate-from-markdown-it.md) |
| mistune | Low — `md(source)` is nearly identical | [Migrate from mistune](https://github.com/lbliii/patitas/blob/main/docs/migrate-from-mistune.md) |
| Python-Markdown | Higher — different dialect and API; no compatibility layer is planned | — |

## When to Choose Which

- **Choose Patitas** if you are on Python 3.14+, want a typed/immutable AST,
  care about free-threading or incremental re-parsing, or want MyST directives
  without extra packages.
- **Choose markdown-it-py** if you need CommonMark on older Python versions or
  already live in the MyST/Sphinx ecosystem.
- **Choose Python-Markdown** if you depend on its long-standing extension
  ecosystem and its specific dialect.
- **Choose mistune** if raw single-thread throughput on a known-trusted dialect
  is your top priority.

## A Note on Honesty

Patitas's [ROADMAP](https://github.com/lbliii/patitas/blob/main/ROADMAP.md)
explicitly lists what it will **not** do:

- **Beating mistune on raw single-thread speed** — the FSM architecture has a
  floor; on the full CommonMark spec the gap is small and imperceptible for
  typical documents. Effort goes to safety, threading, typed AST, and
  incremental parsing instead.
- **A Python-Markdown compatibility layer** — different spec, API, and audience.
- **Python < 3.14 support** — free-threading and modern syntax are core to the
  design.

For current numbers, run the bundled benchmarks yourself rather than trusting a
static table:

```bash
uv pip install mistune markdown-it-py
python benchmarks/benchmark_vs_mistune.py
```

[mdit]: https://github.com/executablebooks/markdown-it-py
[pymd]: https://python-markdown.github.io/
[mistune]: https://github.com/lepture/mistune
