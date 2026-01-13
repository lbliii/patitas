---
title: Plugins
description: Bundle extensions into reusable plugins
draft: false
weight: 20
lang: en
type: doc
tags:
- extending
- plugins
keywords:
- plugins
- extensions
- bundle
category: how-to
icon: puzzle
---

# Plugins

Bundle directives and roles into reusable plugins.

## Plugin Structure

A plugin is a module that registers extensions:

```python
# my_plugin/__init__.py
from patitas.plugins import Plugin
from patitas.directives import DirectiveRegistryBuilder

class MyPlugin(Plugin):
    """My custom plugin."""

    name = "my-plugin"

    def register_directives(self, builder: DirectiveRegistryBuilder) -> None:
        """Register custom directives."""
        from .directives import MyDirective, AnotherDirective

        builder.register(MyDirective())
        builder.register(AnotherDirective())
```

## Using Plugins

Enable plugins when creating a Markdown processor:

```python
from patitas import Markdown

md = Markdown(plugins=["my-plugin"])
html = md(":::{my-directive}\nContent\n:::{/my-directive}")
```

## Built-in Plugins

Patitas includes these plugins:

| Plugin | Description | Directives |
|--------|-------------|------------|
| `directives` | Core directives | admonition, container, dropdown, tabs |
| `math` | Math support | math, equation |
| `table` | Extended tables | table, csv-table |

## Plugin Discovery

Plugins are discovered via entry points:

```toml
# pyproject.toml
[project.entry-points."patitas.plugins"]
my-plugin = "my_plugin:MyPlugin"
```

## Plugin Dependencies

Declare dependencies:

```python
class MyPlugin(Plugin):
    name = "my-plugin"
    dependencies = ["directives"]  # Requires directives plugin
```

## Plugin Configuration

Accept configuration options:

```python
class MyPlugin(Plugin):
    name = "my-plugin"

    def __init__(self, *, option1: str = "default", **kwargs):
        self.option1 = option1

# Usage
md = Markdown(plugins=[("my-plugin", {"option1": "custom"})])
```
