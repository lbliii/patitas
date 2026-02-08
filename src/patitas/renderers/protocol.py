"""ASTRenderer protocol — stable interface for AST renderers.

Any renderer that implements ``render(node) -> str`` conforms to this protocol.
The built-in ``HtmlRenderer`` is the reference implementation.

Example:
    from patitas.renderers.protocol import ASTRenderer

    def render_page(renderer: ASTRenderer, doc: Document) -> str:
        return renderer.render(doc)

"""

from typing import Protocol

from patitas.nodes import Document


class ASTRenderer(Protocol):
    """Protocol for AST renderers.

    Implementations must accept a Document and return a rendered string.
    The built-in ``HtmlRenderer`` conforms to this protocol.

    """

    def render(self, node: Document) -> str:
        """Render a Document AST to a string.

        Args:
            node: The document AST to render.

        Returns:
            Rendered string output.

        """
        ...
