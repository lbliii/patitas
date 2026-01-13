---
title: Inline Syntax
description: Emphasis, strong, code, and other inline elements
draft: false
weight: 10
lang: en
type: doc
tags:
- syntax
- inline
keywords:
- emphasis
- strong
- bold
- italic
- code
category: reference
icon: type
---

# Inline Syntax

Inline elements appear within paragraphs and other block elements.

## Emphasis

Use single asterisks or underscores for emphasis (italic):

```markdown
This is *emphasized* text.
This is _also emphasized_ text.
```

**Result**: This is *emphasized* text.

## Strong

Use double asterisks or underscores for strong (bold):

```markdown
This is **strong** text.
This is __also strong__ text.
```

**Result**: This is **strong** text.

## Combined

Nest emphasis and strong:

```markdown
This is ***bold and italic*** text.
This is **_also bold and italic_** text.
```

## Inline Code

Use backticks for inline code:

```markdown
Use the `parse()` function.
```

**Result**: Use the `parse()` function.

## Strikethrough

Use double tildes for strikethrough (extension):

```markdown
This is ~~deleted~~ text.
```

## Links

See [[docs/syntax/links|Links]] for full link syntax.

```markdown
[Link text](https://example.com)
```

## Images

```markdown
![Alt text](image.png)
![Alt text](image.png "Optional title")
```

## HTML Entities

```markdown
&copy; &mdash; &nbsp;
```

## Escaping

Use backslash to escape special characters:

```markdown
\*not emphasized\*
\[not a link\]
```

## Line Breaks

End a line with two spaces for a hard break:

```markdown
First line  
Second line
```
