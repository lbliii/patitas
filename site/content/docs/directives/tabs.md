---
title: Tabs
description: Tabbed content panels
draft: false
weight: 40
lang: en
type: doc
tags:
- directives
- tabs
keywords:
- tabs
- tabbed
- panels
category: reference
icon: columns
---

# Tabs

Display content in tabbed panels.

## Basic Usage

````markdown
:::{tab-set}

:::{tab-item} Python
```python
print("Hello, World!")
```
:::{/tab-item}

:::{tab-item} JavaScript
```javascript
console.log("Hello, World!");
```
:::{/tab-item}

:::{/tab-set}
````

## Synchronized Tabs

Tabs with the same `sync` key stay synchronized:

````markdown
:::{tab-set}
:sync: lang

:::{tab-item} Python
:sync: python
Python content.
:::{/tab-item}

:::{tab-item} JavaScript
:sync: javascript
JavaScript content.
:::{/tab-item}

:::{/tab-set}
````

## Tab-Set Options

| Option | Type | Description |
|--------|------|-------------|
| `class` | string | Additional CSS classes |
| `sync` | string | Sync group key |

## Tab-Item Options

| Option | Type | Description |
|--------|------|-------------|
| `sync` | string | Sync key within group |
| `selected` | bool | Initially selected tab |
