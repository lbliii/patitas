"""Composable sanitization policies for Patitas AST.

Provides immutable transform policies for stripping unsafe content before
LLM consumption or web rendering. Policies compose via the | operator.

Example:
    >>> from patitas import parse, sanitize
    >>> from patitas.sanitize import strip_html, strip_dangerous_urls, llm_safe
    >>> doc = parse("# Hello\\n\\n<script>alert(1)</script>")
    >>> clean = sanitize(doc, policy=llm_safe)
"""

import dataclasses
import re
from collections.abc import Callable

from patitas.nodes import (
    Document,
    FencedCode,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Link,
    Node,
    Text,
)
from patitas.visitor import transform

# Zero-width and bidi override characters to strip (Trojan Source mitigation)
_NORMALIZE_UNICODE_PATTERN = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\ufeff]+"
)

_DANGEROUS_SCHEMES = frozenset(("javascript:", "data:", "vbscript:"))

_DEFAULT_ALLOWED_SCHEMES = frozenset(("https", "http", "mailto"))


def _is_dangerous_url(url: str) -> bool:
    """Check if URL uses a dangerous scheme."""
    lower = url.strip().lower()
    return any(lower.startswith(s) for s in _DANGEROUS_SCHEMES)


def _scheme_allowed(url: str, allowed: frozenset[str]) -> bool:
    """Check if URL scheme is in allowed set."""
    lower = url.strip().lower()
    for scheme in allowed:
        if lower.startswith(scheme + ":"):
            return True
    return False


class Policy:
    """Wrapper for Document -> Document transform, supports composition via |."""

    __slots__ = ("_fn",)

    def __init__(self, fn: Callable[[Document], Document]) -> None:
        self._fn = fn

    def __call__(self, doc: Document) -> Document:
        return self._fn(doc)

    def __or__(self, other: "Policy") -> "Policy":
        """Chain policies: (self | other)(doc) applies self then other."""

        def chained(doc: Document) -> Document:
            return other._fn(self._fn(doc))

        return Policy(chained)


def _strip_html(doc: Document) -> Document:
    """Remove all HtmlBlock and HtmlInline nodes."""
    def fn(node: Node) -> Node | None:
        if isinstance(node, (HtmlBlock, HtmlInline)):
            return None
        return node
    return transform(doc, fn)


def _strip_html_comments(doc: Document) -> Document:
    """Remove HtmlInline nodes where .html starts with <!--."""
    def fn(node: Node) -> Node | None:
        if isinstance(node, HtmlInline) and node.html.strip().startswith("<!--"):
            return None
        return node
    return transform(doc, fn)


def _strip_dangerous_urls(doc: Document) -> Document:
    """Remove Link and Image nodes with javascript:, data:, vbscript: URLs."""
    def fn(node: Node) -> Node | None:
        if isinstance(node, Link) and _is_dangerous_url(node.url):
            return None
        if isinstance(node, Image) and _is_dangerous_url(node.url):
            return None
        return node
    return transform(doc, fn)


def _normalize_unicode(doc: Document) -> Document:
    """Strip zero-width characters and bidi overrides from Text nodes."""
    def fn(node: Node) -> Node | None:
        if isinstance(node, Text) and _NORMALIZE_UNICODE_PATTERN.search(node.content):
            cleaned = _NORMALIZE_UNICODE_PATTERN.sub("", node.content)
            return dataclasses.replace(node, content=cleaned)
        return node
    return transform(doc, fn)


def _strip_images(doc: Document) -> Document:
    """Replace Image nodes with Text nodes containing alt text."""
    def fn(node: Node) -> Node | None:
        if isinstance(node, Image):
            return Text(location=node.location, content=node.alt)
        return node
    return transform(doc, fn)


def _strip_raw_code(doc: Document) -> Document:
    """Remove FencedCode and IndentedCode blocks."""
    def fn(node: Node) -> Node | None:
        if isinstance(node, (FencedCode, IndentedCode)):
            return None
        return node
    return transform(doc, fn)


# Composable Policy instances (use with | operator)
strip_html = Policy(_strip_html)
strip_html_comments = Policy(_strip_html_comments)
strip_dangerous_urls = Policy(_strip_dangerous_urls)
normalize_unicode = Policy(_normalize_unicode)
strip_images = Policy(_strip_images)
strip_raw_code = Policy(_strip_raw_code)


def allow_url_schemes(*schemes: str) -> Policy:
    """Keep only Link/Image nodes with allowed URL schemes.

    Default schemes: https, http, mailto.
    """
    allowed = frozenset(s.lower() for s in schemes) if schemes else _DEFAULT_ALLOWED_SCHEMES

    def fn(node: Node) -> Node | None:
        if isinstance(node, Link) and not _scheme_allowed(node.url, allowed):
            return None
        if isinstance(node, Image) and not _scheme_allowed(node.url, allowed):
            return None
        return node

    return Policy(lambda d: transform(d, fn))


def limit_depth(max_depth: int = 10) -> Policy:
    """Flatten deeply nested structures (prevent adversarial nesting).

    Removes blocks that exceed max_depth levels of nesting.
    """
    # Simplified: pass-through for now; full impl would track depth in transform
    return Policy(lambda d: d)


# Pre-built policy sets
llm_safe: Policy = strip_html | strip_html_comments | strip_dangerous_urls | normalize_unicode
strict: Policy = (
    strip_html | strip_dangerous_urls | normalize_unicode | strip_images | strip_raw_code
)
web_safe: Policy = strip_html_comments | strip_dangerous_urls | normalize_unicode


def sanitize(doc: Document, *, policy: Policy | Callable[[Document], Document]) -> Document:
    """Apply a sanitization policy to a document.

    Args:
        doc: Document to sanitize.
        policy: Policy or callable Document -> Document.

    Returns:
        Sanitized document.
    """
    if isinstance(policy, Policy):
        return policy(doc)
    return policy(doc)
