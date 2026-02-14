"""MyST-style directives out of the box — admonition, dropdown, tabs."""

from patitas import Markdown

md = Markdown(plugins=["all"])

source = """
:::{note} Optional Title
This is a note admonition.
:::

:::{dropdown} Click to expand
Hidden content here.
:::

:::{tab-set}

:::{tab-item} Python
Python code here.
:::

:::{tab-item} JavaScript
JavaScript code here.
:::

:::
"""

html = md(source)
print(html[:800] + "..." if len(html) > 800 else html)
