# Migrate from markdown-it-py

This guide helps you migrate from
[markdown-it-py](https://github.com/executablebooks/markdown-it-py) to Patitas.
markdown-it-py is widely used across the Python data-science ecosystem (Jupyter,
MyST, Sphinx), so this guide focuses on the concept and API differences you will
hit when moving rendering or AST-processing code over.

## Quick Migration

The high-level render call is a close match:

```python
# Before (markdown-it-py)
from markdown_it import MarkdownIt
md = MarkdownIt()
html = md.render(source)

# After (patitas)
from patitas import Markdown
md = Markdown()
html = md(source)
```

`Markdown.__call__` parses and renders in one step, so `md(source)` is the
direct analogue of `md.render(source)`.

## API Comparison

| markdown-it-py | Patitas | Notes |
|---|---|---|
| `MarkdownIt()` | `Markdown()` | Both default to CommonMark. |
| `MarkdownIt("commonmark")` | `Markdown()` | Patitas is CommonMark by default; there is no preset to choose. |
| `MarkdownIt("gfm-like")` | `Markdown(plugins=["all"])` | Enable GFM-style features explicitly (see [Plugins](#plugins)). |
| `md.render(source)` | `md(source)` or `md.render(doc)` | `md(source)` parses and renders; `md.render(...)` takes a parsed `Document`. |
| `md.parse(source)` -> `list[Token]` | `md.parse(source)` -> `Document` | markdown-it-py returns a flat token stream; Patitas returns a typed AST tree. |
| `md.enable("table")` | `Markdown(plugins=["table"])` | Patitas configures plugins at construction; instances are immutable. |
| `md.disable("emphasis")` | not supported | CommonMark core rules are always on; only plugins are opt-in. |
| `md.use(plugin)` | `Markdown(plugins=[...])` / custom registries | See [Plugins](#plugins) and [Directives and roles](#directives-and-roles). |
| `MarkdownIt(..., {"html": True})` | default renderer (raw HTML passes through) | See [Security and raw HTML](#security-and-raw-html). |

## Plugins

markdown-it-py enables built-in rules with `md.enable(...)` and adds third-party
syntax through `md.use(...)` (often from the `mdit_py_plugins` package). It also
mutates a single instance in place.

Patitas keeps GFM-style syntax **opt-in** through the `plugins=[...]` argument,
and a `Markdown` instance is configured once and then immutable. Plain
`Markdown()` is pure CommonMark. Use `Markdown(plugins=["all"])` to enable every
built-in plugin at once.

Available plugin names: `table`, `strikethrough`, `task_lists`, `footnotes`,
`math`, `autolinks`.

```python
# markdown-it-py — enable a core rule, then add a plugin
from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin

md = MarkdownIt().enable("table").use(footnote_plugin)

# Patitas — declare the plugins you want up front
from patitas import Markdown
md = Markdown(plugins=["table", "footnotes"])
```

| markdown-it-py | Patitas |
|---|---|
| `md.enable("table")` | `Markdown(plugins=["table"])` |
| `md.use(strikethrough_plugin)` (via `mdit_py_plugins`) | `Markdown(plugins=["strikethrough"])` |
| `md.use(tasklists_plugin)` | `Markdown(plugins=["task_lists"])` |
| `md.use(footnote_plugin)` | `Markdown(plugins=["footnotes"])` |
| `md.use(dollarmath_plugin)` | `Markdown(plugins=["math"])` |
| `md.use(linkify_plugin)` / `linkify: True` | `Markdown(plugins=["autolinks"])` |

`autolinks` enables GFM extended autolinks (bare `http(s)://`, `www.`, and
`user@host` emails). CommonMark angle-bracket autolinks `<https://...>` work
without any plugin.

## Tokens vs Typed AST

This is the biggest conceptual difference. markdown-it-py produces a **flat list
of `Token` objects** that you walk with `nesting`/`type` bookkeeping (a token
with `nesting == 1` opens, `-1` closes, `0` is self-closing). Patitas produces a
**typed, immutable AST tree** of dataclasses.

```python
# markdown-it-py — flat token stream
from markdown_it import MarkdownIt
md = MarkdownIt()
tokens = md.parse("# Hello")
for tok in tokens:
    if tok.type == "heading_open":
        print("heading level", tok.tag)  # 'h1'

# Patitas — typed AST tree
from patitas import parse
from patitas.nodes import Heading

doc = parse("# Hello")
for node in doc.children:           # doc.children is a tuple of typed nodes
    if isinstance(node, Heading):
        print("heading level", node.level)  # 1
```

**Patitas advantages:**

- IDE autocomplete and `isinstance` narrowing work on real node types.
- Type errors are caught at development time, not by reading token docs.
- Nodes are frozen and slotted, so an AST is safe to share across threads.

To walk the tree generically, use the visitor/transform helpers instead of
manually tracking token nesting. `BaseVisitor` dispatches to `visit_<snake_case>`
methods and walks children for you:

```python
from patitas import parse, BaseVisitor

class HeadingCounter(BaseVisitor[None]):
    def __init__(self) -> None:
        self.count = 0
    def visit_heading(self, node) -> None:
        self.count += 1

doc = parse("# A\n## B\n")
visitor = HeadingCounter()
visitor.visit(doc)
print(visitor.count)  # 2
```

For tree rewriting, `transform(doc, fn)` applies a function bottom-up and returns
a new immutable tree (return `None` to drop a node).

If you need a serializable structure similar to a token list, Patitas can emit a
plain dict or JSON form of the AST:

```python
from patitas import parse, to_dict, to_json

doc = parse("# Hello")
data = to_dict(doc)   # nested dicts/lists
text = to_json(doc)   # JSON string
```

## Renderer Customization

markdown-it-py customizes output by assigning functions into `md.renderer.rules`
or subclassing `RendererHTML`. Patitas customizes output by subclassing
`HtmlRenderer` (or passing a custom registry), rendering from the typed node:

```python
# markdown-it-py — override a renderer rule
from markdown_it import MarkdownIt
md = MarkdownIt()

def render_heading_open(self, tokens, idx, options, env):
    tokens[idx].attrSet("class", "custom")
    return self.renderToken(tokens, idx, options)

md.add_render_rule("heading_open", render_heading_open)

# Patitas — subclass HtmlRenderer and render from the node
from patitas.renderers.html import HtmlRenderer

class MyRenderer(HtmlRenderer):
    # The _render_* hooks receive a StringBuilder (sb) and a RenderContext (ctx).
    def _render_heading(self, heading, sb, ctx):
        sb.append(f'<h{heading.level} class="custom">')
        self._render_inlines(heading.children, sb, ctx)
        sb.append(f'</h{heading.level}>\n')
```

## Directives and Roles

If you came to markdown-it-py through MyST, you were already writing directives
and roles. Patitas supports MyST-style directives natively, with a stateless
registry instead of in-place plugin mutation:

```python
from patitas import Markdown, directive, create_registry_with_defaults

@directive("my-directive")
def render_my_directive(node, children, sb):
    # `children` is the already-rendered HTML of the body; append to `sb`.
    sb.append(f'<div class="my-directive">{children}</div>')

builder = create_registry_with_defaults()
builder.register(render_my_directive())  # the decorator returns a handler class
md = Markdown(directive_registry=builder.build())
html = md(":::{my-directive}\nContent\n:::")
```

See [Custom Directives](https://lbliii.github.io/patitas/docs/extending/custom-directives/)
for the full handler protocol (including `parse`, typed options, and contracts).

Inline roles such as `` {kbd}`Ctrl` `` use a parallel `RoleRegistryBuilder` /
`role_registry=` argument.

## Security and raw HTML

markdown-it-py disables raw HTML by default and turns it on with `html: True`.
Patitas takes the opposite default: like CommonMark itself, the default renderer
emits raw HTML and `javascript:`/`data:` URLs verbatim (closer to
markdown-it-py's `html: True`). Patitas does **not** silently strip unsafe
content.

To strip unsafe content from untrusted input, sanitize the AST before rendering:

```python
from patitas import parse, sanitize, render
from patitas.sanitize import web_safe

doc = parse(untrusted_source)
html = render(sanitize(doc, policy=web_safe))  # HTML + unsafe URLs removed
```

See [Security](security.md#output-sanitization) for the full threat model.

## Free-threading and parallelism

markdown-it-py mutates one `MarkdownIt` instance during configuration and is not
designed for sharing a parser across free-threaded (3.14t) workers. Patitas is
built for it: configuration is set per-call through a `ContextVar`, AST nodes are
frozen, and a single `Markdown` instance can be reused concurrently. For batch
workloads, `Markdown.parse_many(...)` and `parse_incremental(...)` are available.

See [Thread Safety](https://lbliii.github.io/patitas/docs/about/thread-safety/)
and the [parser comparison](https://lbliii.github.io/patitas/docs/about/comparison/)
for details.

## Performance Notes

Patitas prioritizes ReDoS safety, typed immutable ASTs, and free-threading over
raw single-thread speed. On the full CommonMark spec the bundled benchmark has
shown Patitas roughly on par with markdown-it-py (around 1.2x slower); beating
markdown-it-py or mistune on raw single-thread speed is explicitly **not a
project goal**. Benchmark your own corpus before treating performance as a
migration reason:

```bash
uv pip install mistune markdown-it-py
python benchmarks/benchmark_vs_mistune.py
```

## Why Migrate?

| Reason | Details |
|---|---|
| **Typed AST** | Typed, immutable dataclass tree vs a flat `Token` stream. |
| **Security** | Hand-written O(n) lexer; no regex backtracking (ReDoS-safe). |
| **Free-threading** | Native Python 3.14t support; one instance reused across threads. |
| **Incremental** | `parse_incremental` re-parses only what changed for editor workflows. |
| **MyST syntax** | Directives and roles supported natively without extra plugin packages. |

## Common Issues

### "GFM features (tables, strikethrough) do nothing"

markdown-it-py's `"gfm-like"` preset bundles several extensions. In Patitas each
is a named plugin you opt into:

```python
md = Markdown(plugins=["table", "strikethrough", "task_lists", "autolinks"])
```

### "I can't `enable()`/`disable()` an existing parser"

`Markdown` instances are immutable by design (so they are safe to share across
threads). Construct a new instance with the plugin list you want instead of
mutating one in place.

### "Raw HTML / `javascript:` URLs pass through"

That is CommonMark-default behavior (equivalent to markdown-it-py with
`html: True`). Sanitize the AST with `web_safe` before rendering untrusted input
— see [Security and raw HTML](#security-and-raw-html).

### "Tables look different"

Patitas tracks CommonMark compliance separately from GFM-style plugin behavior;
see [GFM compliance tracking](gfm-compliance.md) before relying on an official
GFM pass count.

## Need Help?

- [Patitas documentation](https://github.com/lbliii/patitas)
- [Open an issue](https://github.com/lbliii/patitas/issues)
- [Parser comparison table](https://lbliii.github.io/patitas/docs/about/comparison/)
- [markdown-it-py documentation](https://markdown-it-py.readthedocs.io/)
