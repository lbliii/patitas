---
title: Directives
description: MyST-style directive extensions for the Patitas Python Markdown parser
draft: false
weight: 30
lang: en
type: doc
tags:
- directives
- myst
keywords:
- directives
- admonition
- tabs
- dropdown
- myst directives
- markdown parser
category: reference
cascade:
  type: doc
icon: layers
---

# Directives

MyST-style directive extensions for enhanced Markdown, documentation sites, and custom
content pipelines.

Directives require the `directives` extra:

```bash
pip install patitas[directives]
```

## Syntax

Directives use the MyST fence syntax:

````markdown
:::{directive-name}
:option: value

Content goes here.

:::{/directive-name}
````

## Available Directives

:::{cards}
:columns: 2
:gap: medium

:::{card} Admonition
:icon: alert-circle
:link: ./admonition
:description: Callout boxes (note, warning, tip)
:::{/card}

:::{card} Container
:icon: square
:link: ./container
:description: Generic wrapper divs
:::{/card}

:::{card} Dropdown
:icon: chevron-down
:link: ./dropdown
:description: Collapsible content sections
:::{/card}

:::{card} Tabs
:icon: columns
:link: ./tabs
:description: Tabbed content panels
:::{/card}

:::{/cards}

## Custom Directives

See [[docs/extending/custom-directives|Custom Directives]] for creating your own.
