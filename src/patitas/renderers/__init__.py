"""Patitas renderers.

Renderers convert typed AST nodes into output formats.

Available Renderers:
- HtmlRenderer: Renders AST to HTML using StringBuilder pattern
- LlmRenderer: Renders AST to structured plain text for LLM consumption

Thread Safety:
All renderers use StringBuilder local to each render() call.
Safe for concurrent use from multiple threads.

"""

from patitas.renderers.html import HtmlRenderer
from patitas.renderers.llm import LlmRenderer

__all__ = ["HtmlRenderer", "LlmRenderer"]
