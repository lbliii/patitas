---
title: Container
description: Generic wrapper divs for styling
draft: false
weight: 20
lang: en
type: doc
tags:
- directives
- container
keywords:
- container
- div
- wrapper
- styling
category: reference
icon: square
---

# Container

Generic wrapper div for applying custom styling.

## Basic Usage

````markdown
:::{container}
Content wrapped in a div.
:::{/container}
````

## Custom Classes

````markdown
:::{container}
:class: my-custom-class

Styled content.
:::{/container}
````

## Multiple Classes

````markdown
:::{container}
:class: highlight centered large

Content with multiple classes.
:::{/container}
````

## Options

| Option | Type | Description |
|--------|------|-------------|
| `class` | string | CSS class(es) to apply |
| `id` | string | HTML id attribute |

## Use Cases

### Centering Content

````markdown
:::{container}
:class: text-center

Centered text and elements.
:::{/container}
````

### Highlighting Sections

````markdown
:::{container}
:class: highlight-box

Important section with custom styling.
:::{/container}
````

### Grid Layouts

````markdown
:::{container}
:class: grid grid-cols-2

:::{container}
Column 1
:::{/container}

:::{container}
Column 2
:::{/container}

:::{/container}
````
