# Patitas Examples Directory — Plan

## Goal

Create an `examples/` directory that showcases Patitas capabilities and entices potential users. Each example should be runnable, self-contained, and highlight a distinct value proposition.

---

## Target Audiences

1. **SSG/docs tool authors** — notebook parsing, incremental, serialization
2. **Editor/live-preview builders** — incremental, differ, visitor
3. **Migration from mistune** — Markdown class, directives
4. **Security-conscious apps** — ReDoS safety, untrusted input
5. **Free-threading adopters** — parallel parsing

---

## Example Structure

```
examples/
  README.md                    # Index with one-liner per example, run instructions
  basic/
    hello_markdown.py          # Simplest: parse + render
    markdown_class.py          # High-level Markdown() API (mistune-like)
  notebooks/
    parse_notebook.py          # Jupyter .ipynb → markdown + metadata
    sample-notebook.ipynb      # Minimal fixture
  ast/
    typed_ast_walk.py          # Visitor: collect headings, extract TOC
    transform_headings.py      # transform(): shift heading levels
  directives/
    builtin_directives.py      # Admonition, dropdown, tabs
    custom_directive.py        # @directive decorator — add your own
  incremental/
    edit_simulation.py         # parse_incremental: edit one para, O(change) re-parse
  differ/
    ast_diff.py                # diff_documents: what changed between two parses
  plugins/
    math_and_tables.py         # Math, tables, footnotes, strikethrough
  advanced/
    parallel_parse.py          # ThreadPoolExecutor — free-threading safe
    serialize_ast.py           # to_json/from_json — cache to disk
```

---

## Example Descriptions

### 1. `basic/hello_markdown.py`
**Hook:** "3 lines to HTML"
```python
from patitas import parse, render
doc = parse("# Hello **World**")
print(render(doc))
```
- Shows parse → render pipeline
- Zero config, zero deps

---

### 2. `basic/markdown_class.py`
**Hook:** "Drop-in for mistune"
```python
from patitas import Markdown
md = Markdown()
html = md("# Hello **World**")
```
- Same API as mistune.create_markdown()
- Migration path for existing projects

---

### 3. `notebooks/parse_notebook.py`
**Hook:** "Parse Jupyter notebooks with zero dependencies"
```python
from patitas import parse_notebook
with open("sample-notebook.ipynb") as f:
    content, metadata = parse_notebook(f.read(), "sample-notebook.ipynb")
print(metadata["title"])
print(content[:200])
```
- Uses `sample-notebook.ipynb` (minimal: 1 markdown cell, 1 code cell, 1 output)
- Highlights: no nbformat, stdlib json only

---

### 4. `ast/typed_ast_walk.py`
**Hook:** "Typed AST — IDE autocomplete, catch errors at dev time"
```python
from patitas import parse
from patitas.visitor import BaseVisitor
from patitas.nodes import Heading

class TocCollector(BaseVisitor):
    def visit_heading(self, node: Heading):
        self.headings.append((node.level, self._heading_text(node)))
    ...

doc = parse(source)
collector = TocCollector()
collector.visit(doc)
```
- Collects headings for TOC
- Shows typed node access (heading.level, children)

---

### 5. `ast/transform_headings.py`
**Hook:** "Immutable AST — transform, don't mutate"
```python
import dataclasses
from patitas import parse, transform
from patitas.nodes import Heading

def shift_headings(node):
    if isinstance(node, Heading):
        return dataclasses.replace(node, level=min(node.level + 1, 6))
    return node

doc = parse("# Top\n## Section")
new_doc = transform(doc, shift_headings)  # ## Top, ### Section
```
- Shifts all heading levels by 1
- Demonstrates immutable transform pattern

---

### 6. `directives/builtin_directives.py`
**Hook:** "MyST-style directives out of the box"
- Renders markdown with `:::{note}`, `:::{dropdown}`, `:::{tab-set}`
- Shows admonition, dropdown, tabs
- Output: HTML with styled callouts

---

### 7. `directives/custom_directive.py`
**Hook:** "Add your own directive in 10 lines"
```python
from patitas import Markdown, create_registry_with_defaults
from patitas.directives.decorator import directive

@directive("callout", options=CalloutOptions)
def render_callout(node, children, sb):
    sb.append(f'<aside class="callout">{children}</aside>')

builder = create_registry_with_defaults()
builder.register(render_callout)
md = Markdown(directive_registry=builder.build())
```
- Extends defaults with custom `:::{callout}`
- Shows @directive decorator

---

### 8. `incremental/edit_simulation.py`
**Hook:** "Re-parse only what changed — O(change) not O(document)"
```python
from patitas import parse, parse_incremental

original = "# Title\n\nFirst para.\n\nSecond para."
doc = parse(original)

# User edits "First para." → "First paragraph."
edit_start = len("# Title\n\n")
edit_end = len("# Title\n\nFirst para.")
new_source = "# Title\n\nFirst paragraph.\n\nSecond para."

new_doc = parse_incremental(new_source, doc, edit_start, edit_end, len("First paragraph."))
# Only the edited block re-parsed; rest reused
```
- Simulates editor edit
- Demonstrates incremental splice

---

### 9. `differ/ast_diff.py`
**Hook:** "Structural diff — know exactly what changed"
```python
from patitas import parse
from patitas.differ import diff_documents

old = parse("# Hello\nWorld")
new = parse("# Hello\nUpdated world")

for change in diff_documents(old, new):
    print(f"{change.kind} at {change.path}: {change.old_node} → {change.new_node}")
```
- Use case: live preview, cache invalidation, change notifications

---

### 10. `plugins/math_and_tables.py`
**Hook:** "Tables, math, footnotes — enable what you need"
```python
from patitas import Markdown

md = Markdown(plugins=["table", "math", "footnotes"])
html = md("""
| A | B |
|---|---|
| 1 | 2 |

$$E = mc^2$$

Here[^1] is a footnote.

[^1]: The footnote text.
""")
```
- Shows plugin activation
- Renders table, math block, footnote

---

### 11. `advanced/parallel_parse.py`
**Hook:** "Free-threading safe — parse 1000 docs in parallel"
```python
from concurrent.futures import ThreadPoolExecutor
from patitas import parse

docs = ["# Doc " + str(i) for i in range(1000)]
with ThreadPoolExecutor(max_workers=8) as ex:
    results = list(ex.map(parse, docs))
```
- No shared mutable state
- Python 3.14t ready

---

### 12. `advanced/serialize_ast.py`
**Hook:** "Cache parsed AST to disk — JSON round-trip"
```python
from patitas import parse
from patitas.serialization import to_json, from_json

doc = parse("# Cached document")
json_str = to_json(doc)
# ... write to disk, read later ...
restored = from_json(json_str)
assert doc == restored
```
- Use case: incremental builds, offline processing

---

## Optional: Syntax Highlighting

If `patitas[syntax]` is installed:
```python
# examples/plugins/syntax_highlighting.py
from patitas import Markdown
md = Markdown(highlight=True)
html = md("```python\ndef hello(): pass\n```")
```

Could be a 13th example or folded into `plugins/math_and_tables.py` as a note.

---

## examples/README.md Structure

```markdown
# Patitas Examples

Runnable examples showcasing Patitas capabilities. Run from repo root:

    python examples/basic/hello_markdown.py
    python examples/notebooks/parse_notebook.py
    ...

| Example | What it shows |
|---------|----------------|
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

Requirements: `pip install patitas` (or `patitas[syntax]` for highlighting)
```

---

## Implementation Order

1. **Phase 1 — Core appeal**
   - `basic/hello_markdown.py`
   - `basic/markdown_class.py`
   - `notebooks/parse_notebook.py` + `sample-notebook.ipynb`

2. **Phase 2 — Differentiators**
   - `ast/typed_ast_walk.py`
   - `directives/builtin_directives.py`
   - `directives/custom_directive.py`

3. **Phase 3 — Advanced**
   - `incremental/edit_simulation.py`
   - `differ/ast_diff.py`
   - `plugins/math_and_tables.py`

4. **Phase 4 — Power users**
   - `advanced/parallel_parse.py`
   - `advanced/serialize_ast.py`
   - `ast/transform_headings.py` (if transform API is straightforward)

---

## Notes

- Each example should be **self-contained** — no shared helpers unless trivial
- **Print output** so users see results when they run it
- Keep examples **short** — 20–40 lines max per file
- `sample-notebook.ipynb`: 2–3 cells (markdown, code with output), nbformat 4
