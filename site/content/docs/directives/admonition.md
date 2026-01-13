---
title: Admonition
description: Callout boxes for notes, warnings, and tips
draft: false
weight: 10
lang: en
type: doc
tags:
- directives
- admonition
keywords:
- admonition
- note
- warning
- tip
- callout
category: reference
icon: alert-circle
---

# Admonition

Callout boxes for highlighting important information.

## Basic Usage

````markdown
:::{note}
This is a note.
:::{/note}
````

## Types

### Note

````markdown
:::{note}
General information.
:::{/note}
````

### Warning

````markdown
:::{warning}
Potential issues to be aware of.
:::{/warning}
````

### Tip

````markdown
:::{tip}
Helpful suggestions.
:::{/tip}
````

### Important

````markdown
:::{important}
Critical information.
:::{/important}
````

### Caution

````markdown
:::{caution}
Proceed with care.
:::{/caution}
````

### Danger

````markdown
:::{danger}
Risk of data loss or security issues.
:::{/danger}
````

## Custom Titles

````markdown
:::{note} Custom Title
Content with a custom title.
:::{/note}
````

## Options

| Option | Type | Description |
|--------|------|-------------|
| `class` | string | Additional CSS classes |
| `name` | string | Reference target name |

## Nesting

Admonitions can contain any Markdown:

````markdown
:::{note}
This note contains:

- A list
- With items

```python
# And code
print("Hello")
```
:::{/note}
````
