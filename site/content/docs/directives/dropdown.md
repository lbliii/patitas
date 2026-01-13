---
title: Dropdown
description: Collapsible content sections
draft: false
weight: 30
lang: en
type: doc
tags:
- directives
- dropdown
keywords:
- dropdown
- collapsible
- details
category: reference
icon: chevron-down
---

# Dropdown

Collapsible content sections using HTML `<details>` element.

## Basic Usage

````markdown
:::{dropdown} Click to expand
Hidden content goes here.
:::{/dropdown}
````

## Open by Default

````markdown
:::{dropdown} Already expanded
:open:

This content is visible by default.
:::{/dropdown}
````

## Options

| Option | Type | Description |
|--------|------|-------------|
| `open` | bool | Expand by default |
| `class` | string | Additional CSS classes |
| `icon` | string | Custom icon name |

## Styling

Combine with admonition types:

````markdown
:::{dropdown} Warning Details
:class: warning

Additional warning information.
:::{/dropdown}
````

## Nesting

Dropdowns can contain any Markdown including other directives:

````markdown
:::{dropdown} Outer dropdown

:::{note}
A note inside a dropdown.
:::{/note}

:::{dropdown} Nested dropdown
Inception!
:::{/dropdown}

:::{/dropdown}
````
