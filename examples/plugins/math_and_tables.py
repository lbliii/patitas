"""Tables, math, footnotes — enable what you need via plugins."""

from patitas import Markdown

md = Markdown(plugins=["table", "math", "footnotes"])

source = """
| A | B |
|---|---|
| 1 | 2 |

Inline math: $E = mc^2$

Block math:

$$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$$

Here[^1] is a footnote.

[^1]: The footnote text.
"""

html = md(source)
print(html[:600] + "..." if len(html) > 600 else html)
