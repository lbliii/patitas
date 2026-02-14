"""High-level Markdown API — drop-in for mistune."""

from patitas import Markdown

md = Markdown()
html = md("# Hello **World**")
print(html)
