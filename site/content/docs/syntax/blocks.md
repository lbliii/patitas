---
title: Block Syntax
description: Paragraphs, headings, lists, and other block elements
draft: false
weight: 20
lang: en
type: doc
tags:
- syntax
- blocks
keywords:
- paragraphs
- headings
- lists
- blockquotes
category: reference
icon: layout
---

# Block Syntax

Block elements form the structure of a Markdown document.

## Paragraphs

Separate paragraphs with blank lines:

```markdown
First paragraph.

Second paragraph.
```

## Headings

### ATX Headings

```markdown
# Heading 1
## Heading 2
### Heading 3
#### Heading 4
##### Heading 5
###### Heading 6
```

### Setext Headings

```markdown
Heading 1
=========

Heading 2
---------
```

## Lists

### Unordered Lists

```markdown
- Item one
- Item two
- Item three
```

Or with `*` or `+`:

```markdown
* Item one
+ Item one
```

### Ordered Lists

```markdown
1. First item
2. Second item
3. Third item
```

Numbers don't need to be sequential:

```markdown
1. First item
1. Second item
1. Third item
```

### Nested Lists

```markdown
- Item one
  - Nested item
  - Another nested
- Item two
```

## Blockquotes

```markdown
> This is a blockquote.
>
> It can span multiple paragraphs.
```

Nested blockquotes:

```markdown
> First level
>> Second level
>>> Third level
```

## Horizontal Rules

```markdown
---
***
___
```

## Code Blocks

See [[docs/syntax/code|Code]] for fenced and indented code blocks.
