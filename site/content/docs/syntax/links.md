---
title: Links
description: Inline links, reference links, and autolinks
draft: false
weight: 30
lang: en
type: doc
tags:
- syntax
- links
keywords:
- links
- urls
- references
- autolinks
category: reference
icon: link
---

# Links

Various ways to create links in Markdown.

## Inline Links

```markdown
[Link text](https://example.com)
[Link with title](https://example.com "Title")
```

## Reference Links

Define links once, use multiple times:

```markdown
[Link text][ref]
[Another link][ref]

[ref]: https://example.com
```

Shorthand (link text = reference):

```markdown
[example.com]

[example.com]: https://example.com
```

## Autolinks

URLs and emails are automatically linked:

```markdown
<https://example.com>
<user@example.com>
```

## Relative Links

```markdown
[Local page](./other-page.md)
[Parent directory](../index.md)
```

## Fragment Links

```markdown
[Section](#heading-id)
[Other page section](./page.md#section)
```

## Images as Links

```markdown
[![Alt text](image.png)](https://example.com)
```
