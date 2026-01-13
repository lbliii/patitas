---
title: Code
description: Inline code, fenced blocks, and indented code
draft: false
weight: 40
lang: en
type: doc
tags:
- syntax
- code
keywords:
- code
- fenced
- syntax highlighting
- indented
category: reference
icon: terminal
---

# Code

Display code in Markdown documents.

## Inline Code

Use backticks for inline code:

```markdown
Use the `parse()` function.
```

Escape backticks with more backticks:

```markdown
`` `code` with backticks ``
```

## Fenced Code Blocks

Use triple backticks:

````markdown
```python
def hello():
    print("Hello, World!")
```
````

Or triple tildes:

````markdown
~~~python
def hello():
    print("Hello, World!")
~~~
````

## Language Hints

Specify language for syntax highlighting:

````markdown
```python
import patitas
```

```javascript
console.log("Hello");
```

```bash
pip install patitas
```
````

## Indented Code Blocks

Indent with 4 spaces:

```markdown
    def hello():
        print("Hello")
```

## Code in Lists

Indent code blocks in lists:

```markdown
1. First step:

   ```python
   parse("# Hello")
   ```

2. Second step
```

## Syntax Highlighting

Install the `syntax` extra for highlighting:

```bash
pip install patitas[syntax]
```

Then use the Rosettes highlighter:

```python
from patitas import Markdown
from patitas.highlighting import set_highlighter
from rosettes import highlight

set_highlighter(highlight)

md = Markdown()
html = md("```python\nprint('hello')\n```")
```
