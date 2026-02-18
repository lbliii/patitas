# Patitas Examples

Runnable examples showcasing Patitas capabilities. Run from repo root:

```bash
python examples/basic/hello_markdown.py
python examples/notebooks/parse_notebook.py
# etc.
```

Or with `uv run`:

```bash
uv run python examples/basic/hello_markdown.py
```

## Examples

| Example | What it shows |
|---------|---------------|
| [basic/hello_markdown.py](basic/hello_markdown.py) | Parse + render in 3 lines |
| [basic/markdown_class.py](basic/markdown_class.py) | High-level API (mistune-like) |
| [notebooks/parse_notebook.py](notebooks/parse_notebook.py) | Jupyter .ipynb parsing, zero deps |
| [ast/typed_ast_walk.py](ast/typed_ast_walk.py) | Visitor: collect headings for TOC |
| [ast/transform_headings.py](ast/transform_headings.py) | Immutable AST transform |
| [directives/builtin_directives.py](directives/builtin_directives.py) | Admonition, dropdown, tabs |
| [directives/custom_directive.py](directives/custom_directive.py) | Add your own directive |
| [incremental/edit_simulation.py](incremental/edit_simulation.py) | O(change) re-parse |
| [differ/ast_diff.py](differ/ast_diff.py) | Structural diff between parses |
| [plugins/math_and_tables.py](plugins/math_and_tables.py) | Tables, math, footnotes |
| [advanced/parallel_parse.py](advanced/parallel_parse.py) | Free-threading safe parallel parse |
| [advanced/serialize_ast.py](advanced/serialize_ast.py) | JSON round-trip for caching |
| [llm_safety/llm_safe_context.py](llm_safety/llm_safe_context.py) | Sanitize + render markdown for LLM context |

## Requirements

- `pip install patitas` (or `uv sync` in repo)
- Optional: `pip install patitas[syntax]` for syntax highlighting in code blocks
