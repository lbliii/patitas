"""Add your own directive in ~10 lines — extend defaults with @directive."""

from patitas import Markdown, create_registry_with_defaults
from patitas.directives.decorator import directive


@directive("callout")
def render_callout(node, children: str, sb) -> None:
    """Render :::callout content as a styled aside."""
    sb.append(f'<aside class="callout">{children}</aside>')


builder = create_registry_with_defaults()
builder.register(render_callout())

md = Markdown(directive_registry=builder.build())

source = """
:::{callout}
This is a custom callout directive!
:::
"""

html = md(source)
print(html)
