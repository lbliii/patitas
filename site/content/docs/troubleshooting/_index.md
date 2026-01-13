---
title: Troubleshooting
description: Common errors and how to fix them
draft: false
weight: 70
lang: en
type: doc
tags:
- troubleshooting
- errors
keywords:
- troubleshooting
- errors
- debugging
category: how-to
cascade:
  type: doc
icon: alert-triangle
---

# Troubleshooting

Solutions to common issues.

## Import Errors

### ModuleNotFoundError: No module named 'patitas'

**Cause**: Patitas is not installed.

**Solution**:

```bash
pip install patitas
```

### ImportError: cannot import name 'DirectiveHandler'

**Cause**: Directives extra not installed.

**Solution**:

```bash
pip install patitas[directives]
```

## Parsing Issues

### Unexpected output format

**Cause**: Input may have unexpected whitespace or encoding.

**Solution**: Check encoding and normalize:

```python
source = source.replace('\r\n', '\n')
doc = parse(source)
```

### Directive not recognized

**Cause**: Directive not registered or misspelled.

**Solution**: Check directive name matches exactly:

```python
# Correct
:::{note}
Content
:::{/note}

# Wrong
:::{Note}  # Case-sensitive
```

## Rendering Issues

### Empty HTML output

**Cause**: Source not passed to render.

**Solution**: Pass source for zero-copy extraction:

```python
from patitas import parse, render

source = "# Hello"
doc = parse(source)
html = render(doc, source=source)  # Include source!
```

### Code not highlighted

**Cause**: Highlighter not set.

**Solution**: Set a highlighter:

```python
from patitas.highlighting import set_highlighter

set_highlighter(my_highlighter)
```

## Performance Issues

### Slow parsing

**Cause**: Very large documents or complex nesting.

**Solution**: Consider splitting documents or using streaming.

### High memory usage

**Cause**: Holding many ASTs in memory.

**Solution**: Process and release ASTs incrementally:

```python
for source in sources:
    doc = parse(source)
    html = render(doc, source=source)
    # doc is garbage collected after this iteration
```

## Getting Help

- [GitHub Issues](https://github.com/lbliii/patitas/issues)
- [API Reference](/docs/reference/api/)
