---
title: Examples
description: Runnable examples showcasing Patitas capabilities
draft: false
weight: 30
lang: en
type: doc
tags:
- examples
- quickstart
keywords:
- examples
- tutorial
- runnable
category: onboarding
icon: play
---

# Examples

Runnable examples are in the `examples/` directory of the Patitas repo. Run from repo root:

```bash
python examples/basic/hello_markdown.py
```

Or with `uv run`:

```bash
uv run python examples/basic/hello_markdown.py
```

## Example Index

| Example | What it shows |
|---------|---------------|
| [basic/hello_markdown.py](https://github.com/lbliii/patitas/blob/main/examples/basic/hello_markdown.py) | Parse + render in 3 lines |
| [basic/markdown_class.py](https://github.com/lbliii/patitas/blob/main/examples/basic/markdown_class.py) | High-level API (mistune-like) |
| [notebooks/parse_notebook.py](https://github.com/lbliii/patitas/blob/main/examples/notebooks/parse_notebook.py) | Jupyter .ipynb parsing, zero deps |
| [ast/typed_ast_walk.py](https://github.com/lbliii/patitas/blob/main/examples/ast/typed_ast_walk.py) | Visitor: collect headings for TOC |
| [ast/transform_headings.py](https://github.com/lbliii/patitas/blob/main/examples/ast/transform_headings.py) | Immutable AST transform |
| [directives/builtin_directives.py](https://github.com/lbliii/patitas/blob/main/examples/directives/builtin_directives.py) | Admonition, dropdown, tabs |
| [directives/custom_directive.py](https://github.com/lbliii/patitas/blob/main/examples/directives/custom_directive.py) | Add your own directive |
| [incremental/edit_simulation.py](https://github.com/lbliii/patitas/blob/main/examples/incremental/edit_simulation.py) | O(change) re-parse |
| [differ/ast_diff.py](https://github.com/lbliii/patitas/blob/main/examples/differ/ast_diff.py) | Structural diff between parses |
| [plugins/math_and_tables.py](https://github.com/lbliii/patitas/blob/main/examples/plugins/math_and_tables.py) | Tables, math, footnotes |
| [advanced/parallel_parse.py](https://github.com/lbliii/patitas/blob/main/examples/advanced/parallel_parse.py) | Free-threading safe parallel parse |
| [advanced/serialize_ast.py](https://github.com/lbliii/patitas/blob/main/examples/advanced/serialize_ast.py) | JSON round-trip for caching |
| [llm_safety/llm_safe_context.py](https://github.com/lbliii/patitas/blob/main/examples/llm_safety/llm_safe_context.py) | Sanitize + render markdown for LLM context |

## Requirements

- `pip install patitas` (or `uv sync` in repo)
- Optional: `pip install patitas[syntax]` for syntax highlighting in code blocks

## See Also

- [[docs/extending/llm-safety|LLM Safety]] — Full guide for the parse → sanitize → render_llm pipeline
- [[docs/reference/api|API Reference]] — Complete API documentation
