# Migrate from mistune

This guide helps you migrate from mistune to Patitas.

## Quick Migration

The basic API is nearly identical:

```python
# Before (mistune)
import mistune
md = mistune.create_markdown()
html = md(source)

# After (patitas)
from patitas import Markdown
md = Markdown()
html = md(source)
```

## API Comparison

| mistune | Patitas | Notes |
|---------|---------|-------|
| `mistune.create_markdown()` | `Markdown()` | Same pattern |
| `md(source)` | `md(source)` | Identical |
| `mistune.html(source)` | `parse()` + `render()` | Separate functions |

## Plugins

### Tables

```python
# mistune
md = mistune.create_markdown(plugins=['table'])

# Patitas — tables enabled by default via plugins
from patitas import Markdown
md = Markdown()  # Tables work out of the box
```

### Strikethrough

```python
# mistune
md = mistune.create_markdown(plugins=['strikethrough'])

# Patitas — enabled by default
md = Markdown()  # ~~strikethrough~~ works
```

### Footnotes

```python
# mistune
md = mistune.create_markdown(plugins=['footnotes'])

# Patitas — enabled by default
md = Markdown()  # [^1] footnotes work
```

## Directives

This is the biggest difference. mistune uses RST-style syntax, Patitas uses MyST:

```markdown
# mistune (RST-style)
.. note::
   This is a note.

# Patitas (MyST-style)
:::{note}
This is a note.
:::
```

### Converting Directive Syntax

| mistune | Patitas |
|---------|---------|
| `.. note::` | `:::{note}` |
| `.. warning::` | `:::{warning}` |
| `.. admonition:: Title` | `:::{admonition} Title` |

### Custom Directives

```python
# mistune
from mistune.directives import RSTDirective

class MyDirective:
    def parse(self, block, m, state):
        ...
    def __call__(self, md):
        md.block.register_rule('mydirective', ...)

md = mistune.create_markdown(plugins=[RSTDirective([MyDirective()])])

# Patitas
from patitas import Markdown, create_registry_with_defaults

class MyDirective:
    names = ("mydirective",)
    token_type = "mydirective"
    
    def render(self, directive, renderer):
        return f'<div class="mydirective">{directive.title}</div>'

builder = create_registry_with_defaults()
builder.register(MyDirective())
md = Markdown(directive_registry=builder.build())
```

## AST Access

```python
# mistune — Dict[str, Any]
tokens = mistune.create_markdown(renderer=None)(source)
# tokens is a list of dicts

# Patitas — Typed dataclasses
from patitas import parse
from patitas.nodes import Heading, Paragraph

doc = parse(source)
# doc.children is tuple of typed nodes

for node in doc.children:
    if isinstance(node, Heading):
        print(f"Heading level {node.level}")
```

**Patitas advantages:**
- IDE autocomplete works
- Type errors caught at development time
- Nodes are immutable (safe to share)

## Renderer Customization

```python
# mistune — subclass BaseRenderer
class MyRenderer(mistune.BaseRenderer):
    def heading(self, text, level):
        return f'<h{level} class="custom">{text}</h{level}>'

md = mistune.create_markdown(renderer=MyRenderer())

# Patitas — pass custom registry with render methods
# Or subclass HtmlRenderer
from patitas.renderers.html import HtmlRenderer

class MyRenderer(HtmlRenderer):
    def _render_heading(self, heading, sb):
        sb.append(f'<h{heading.level} class="custom">')
        self._render_inlines(heading.children, sb)
        sb.append(f'</h{heading.level}>\n')
```

## Performance Notes

Patitas is typically 40-50% faster than mistune:

```bash
# Run benchmark
pip install mistune
python benchmarks/benchmark_vs_mistune.py
```

## Why Migrate?

| Reason | Details |
|--------|---------|
| **Security** | Patitas is ReDoS-proof; mistune uses regex |
| **Performance** | 40-50% faster on typical documents |
| **Type Safety** | Typed AST vs Dict[str, Any] |
| **Free-threading** | Native Python 3.14t support |
| **MyST Syntax** | Modern directive syntax, Jupyter Book compatible |

## Common Issues

### "Directive not rendering"

MyST syntax requires `:::` (three colons), not RST's `..`:

```markdown
# Wrong (RST syntax)
.. note::
   Content

# Correct (MyST syntax)
:::{note}
Content
:::
```

### "HTML not rendering"

By default, Patitas escapes HTML for security. To allow raw HTML:

```python
# Enable raw HTML in content
md = Markdown()
html = md(source)  # HTML is escaped by default
```

### "Tables look different"

Both parsers support GFM tables, but rendering may differ slightly. Patitas follows CommonMark/GFM spec strictly.

## Need Help?

- [Patitas documentation](https://github.com/lbliii/patitas)
- [Open an issue](https://github.com/lbliii/patitas/issues)
- [MyST Markdown reference](https://myst-parser.readthedocs.io/)
