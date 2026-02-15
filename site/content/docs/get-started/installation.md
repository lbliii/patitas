---
title: Installation
description: Install Patitas and optional extras
draft: false
weight: 10
lang: en
type: doc
tags:
- installation
- setup
keywords:
- pip
- install
- uv
- requirements
category: onboarding
icon: download
---

# Installation

## Requirements

:::{checklist} Prerequisites
:show-progress:
- [ ] Python 3.14 or later installed
- [x] No runtime dependencies (core)
:::{/checklist}

## Install

:::{tab-set}
:::{tab-item} uv
:badge: Recommended

```bash
uv add patitas
```

:::{/tab-item}

:::{tab-item} pip

```bash
pip install patitas
```

:::{/tab-item}

:::{tab-item} From Source

```bash
git clone https://github.com/lbliii/patitas.git
cd patitas
uv sync --group dev
```

:::{/tab-item}
:::{/tab-set}

## Optional Extras

Patitas uses a tiered installation model:

:::{tab-set}
:::{tab-item} Directives

MyST-style directives (admonition, tabs, dropdown, container):

```bash
pip install patitas[directives]
```

:::{/tab-item}

:::{tab-item} Syntax Highlighting

Code block syntax highlighting via Rosettes:

```bash
pip install patitas[syntax]
```

:::{/tab-item}

:::{tab-item} Bengal Integration

Full Bengal directive suite:

```bash
pip install patitas[bengal]
```

:::{/tab-item}

:::{tab-item} Everything

All extras except Bengal:

```bash
pip install patitas[all]
```

:::{/tab-item}
:::{/tab-set}

## Verify Installation

```python
>>> import patitas
>>> patitas.parse("# Hello")
(Heading(level=1, ...),)
```

## Next Steps

:::{related}
:limit: 3
:section_title: Next Steps
:::
