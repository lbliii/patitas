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

- Python 3.14 or later
- No runtime dependencies (core)

## pip

```bash
pip install patitas
```

## uv (recommended)

```bash
uv add patitas
```

## Optional Extras

Patitas uses a tiered installation model:

### Directives

MyST-style directives (admonition, tabs, dropdown, container):

```bash
pip install patitas[directives]
```

### Syntax Highlighting

Code block syntax highlighting via Rosettes:

```bash
pip install patitas[syntax]
```

### Bengal Integration

Full Bengal directive suite:

```bash
pip install patitas[bengal]
```

### Everything

All extras except Bengal:

```bash
pip install patitas[all]
```

## Development Installation

```bash
git clone https://github.com/lbliii/patitas.git
cd patitas
uv sync --group dev
```

## Verify Installation

```python
>>> import patitas
>>> patitas.parse("# Hello")
(Heading(level=1, ...),)
```
