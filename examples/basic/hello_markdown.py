"""Parse and render Markdown in 3 lines — zero config, zero deps."""

from patitas import parse, render

doc = parse("# Hello **World**")
html = render(doc)
print(html)
