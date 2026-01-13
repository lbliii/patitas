"""
Patitas — Modern Markdown Parser for Python 3.14t

A CommonMark-compliant Markdown parser designed for free-threaded Python.
Features O(n) guaranteed parsing, typed AST, and zero runtime dependencies.

Quick Start:
    >>> from patitas import parse, render
    >>> doc = parse("# Hello, World!")
    >>> html = render(doc)
    >>> print(html)
    <h1>Hello, World!</h1>

Installation Tiers:
    pip install patitas              # Core parser (zero deps)
    pip install patitas[directives]  # + Portable directives
    pip install patitas[syntax]      # + Syntax highlighting via Rosettes
    pip install patitas[bengal]      # + Full Bengal directive suite
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = [
    # Version
    "__version__",
    # Core API (to be implemented)
    # "parse",
    # "render",
    # "Markdown",
    # Node types (to be exported from nodes.py)
    # "Document",
    # "Heading",
    # "Paragraph",
    # ...
]

# =============================================================================
# Core API
# =============================================================================
# These will be implemented after extraction from Bengal:
#
# from patitas.parser import Parser
# from patitas.nodes import Document
# from patitas.renderers.html import HtmlRenderer
#
# def parse(source: str, *, plugins: list | None = None) -> Document:
#     """Parse Markdown source into a typed AST."""
#     parser = Parser(plugins=plugins or [])
#     return parser.parse(source)
#
# def render(doc: Document, *, renderer: HtmlRenderer | None = None) -> str:
#     """Render an AST Document to HTML."""
#     renderer = renderer or HtmlRenderer()
#     return renderer.render(doc)
#
# class Markdown:
#     """High-level Markdown processor combining parser and renderer."""
#
#     def __init__(
#         self,
#         *,
#         plugins: list | None = None,
#         renderer: HtmlRenderer | None = None,
#     ) -> None:
#         self._parser = Parser(plugins=plugins or [])
#         self._renderer = renderer or HtmlRenderer()
#
#     def __call__(self, source: str) -> str:
#         """Parse and render Markdown in one call."""
#         doc = self._parser.parse(source)
#         return self._renderer.render(doc)
#
#     def parse(self, source: str) -> Document:
#         """Parse Markdown source into AST."""
#         return self._parser.parse(source)
#
#     def render(self, doc: Document) -> str:
#         """Render AST to HTML."""
#         return self._renderer.render(doc)
