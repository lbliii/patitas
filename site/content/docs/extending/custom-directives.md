---
title: Custom Directives
description: Create your own directive handlers
draft: false
weight: 10
lang: en
type: doc
tags:
- extending
- directives
keywords:
- custom
- directives
- handlers
category: how-to
icon: layers
---

# Custom Directives

Create directive handlers to extend Markdown syntax.

## DirectiveHandler Protocol

Implement the `DirectiveHandler` protocol:

```python
from patitas.directives import DirectiveHandler
from patitas.nodes import Block, Directive
from patitas.location import SourceLocation
from patitas.stringbuilder import StringBuilder

class MyDirective:
    """Custom directive handler."""

    name = "my-directive"

    def parse(
        self,
        *,
        title: str,
        options: dict[str, str],
        content: str,
        location: SourceLocation | None = None,
    ) -> Block | None:
        """Parse directive into AST node."""
        return Directive(
            name=self.name,
            title=title,
            options=options,
            raw_content=content,
            children=(),
            location=location,
        )

    def render(
        self,
        node: Directive,
        out: StringBuilder,
        render_children: callable,
    ) -> None:
        """Render directive to HTML."""
        out.append(f'<div class="my-directive">')
        out.append(f'<h4>{node.title}</h4>')
        out.append(f'<p>{node.raw_content}</p>')
        out.append('</div>')
```

## Registering Directives

Use `DirectiveRegistry`:

```python
from patitas.directives import DirectiveRegistry, DirectiveRegistryBuilder

# Build a registry
builder = DirectiveRegistryBuilder()
builder.register(MyDirective())

registry = builder.build()
```

## Options Parsing

Use typed options classes:

```python
from patitas.directives import DirectiveOptions

class MyOptions(DirectiveOptions):
    color: str = "blue"
    size: int = 12
    enabled: bool = True

class MyDirective:
    name = "styled"
    options_class = MyOptions

    def parse(self, *, options: dict[str, str], **kwargs):
        parsed = MyOptions.from_dict(options)
        # parsed.color, parsed.size, parsed.enabled are typed
```

## Contracts

Enforce nesting rules with contracts:

```python
from patitas.directives import DirectiveContract

TAB_SET_CONTRACT = DirectiveContract(
    required_children=["tab-item"],
    allowed_children=["tab-item"],
)

class TabSetDirective:
    name = "tab-set"
    contract = TAB_SET_CONTRACT
```

## Parse-Only and Render-Only

For simpler cases:

```python
from patitas.directives import DirectiveParseOnly, DirectiveRenderOnly

class ParseOnlyDirective(DirectiveParseOnly):
    name = "parse-only"

    def parse(self, **kwargs) -> Block | None:
        # Only parsing, use default renderer
        pass

class RenderOnlyDirective(DirectiveRenderOnly):
    name = "render-only"

    def render(self, node, out, render_children) -> None:
        # Only rendering, use default parser
        pass
```
