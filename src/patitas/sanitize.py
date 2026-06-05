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
import html as _html
import re
from collections.abc import Callable

from patitas.nodes import (
    BlockQuote,
    Directive,
    Document,
    FencedCode,
    HtmlBlock,
    HtmlInline,
    Image,
    IndentedCode,
    Link,
    List,
    ListItem,
    Node,
    Text,
)
from patitas.visitor import transform

# Zero-width and bidi override characters to strip (Trojan Source mitigation)
_NORMALIZE_UNICODE_PATTERN = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e\ufeff]+"
)

_DANGEROUS_SCHEMES = frozenset(("javascript", "data", "vbscript"))

_DEFAULT_ALLOWED_SCHEMES = frozenset(("https", "http", "mailto"))

# A URL scheme is an ASCII letter followed by letters/digits/+/-/. (RFC 3986).
_URL_SCHEME_RE = re.compile(r"[a-z][a-z0-9+.\-]*")


def _url_scheme(url: str) -> str | None:
    """Extract a URL's scheme, robust to obfuscation; None if scheme-less.

    Browsers ignore HTML entities and embedded control/whitespace characters
    when resolving a URL scheme, so ``javascript:`` can hide as
    ``&#106;avascript:`` or ``java&Tab;script:``. We decode entities and strip
    ASCII control/whitespace before reading the scheme so the dangerous-scheme
    check cannot be bypassed.

    Returns the lowercased scheme (without the trailing colon), or None for
    scheme-less URLs (relative paths, fragments, protocol-relative ``//``),
    which are always safe.
    """
    decoded = _html.unescape(url)
    # Drop ASCII control chars and whitespace (everything <= 0x20, plus DEL).
    stripped = "".join(ch for ch in decoded if 0x20 < ord(ch) != 0x7F)
    colon = stripped.find(":")
    if colon <= 0:
        return None
    scheme = stripped[:colon].lower()
    return scheme if _URL_SCHEME_RE.fullmatch(scheme) else None


def _is_dangerous_url(url: str) -> bool:
    """Check if a URL uses a known-dangerous scheme (after de-obfuscation)."""
    scheme = _url_scheme(url)
    return scheme is not None and scheme in _DANGEROUS_SCHEMES


def _scheme_allowed(url: str, allowed: frozenset[str]) -> bool:
    """Check if a URL's scheme is allowed.

    Scheme-less/relative URLs (``/path``, ``#frag``, ``//host``) are always
    allowed; only an explicit, disallowed scheme is rejected.
    """
    scheme = _url_scheme(url)
    return scheme is None or scheme in allowed


class Policy:
    """Wrapper for Document -> Document transform, supports composition via |."""

    __slots__ = ("_fn",)

    def __init__(self, fn: Callable[[Document], Document]) -> None:
        self._fn = fn

    def __call__(self, doc: Document) -> Document:
        return self._fn(doc)

    def __or__(self, other: Policy) -> Policy:
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


# Block container nodes that add a level of nesting depth.
_DEPTH_CONTAINERS = (BlockQuote, List, ListItem, Directive)

# Nodes whose children are themselves blocks (so recursion stays in the block
# tree). Document is the root and does not count as a nesting level. Everything
# else — leaf blocks and inline-bearing blocks like Paragraph/Heading — is a
# leaf for depth purposes, so inline content is never traversed.
_BLOCK_CHILD_NODES = (Document, BlockQuote, List, ListItem, Directive)


def limit_depth(max_depth: int = 10) -> Policy:
    """Prune block content nested deeper than ``max_depth`` container levels.

    Depth counts block containers (block quotes, lists, list items, directives).
    Containers at the limit have their children dropped, protecting downstream
    consumers from adversarially deep AST nesting.

    Only block-level structure is traversed. Inline children (e.g. ``Emphasis``,
    ``Strong``, ``Link`` text) do not contribute to block nesting depth and are
    left untouched, so ``limit_depth`` cannot itself recurse into — and crash on —
    deeply nested inline content.

    Note:
        For untrusted *input*, prefer the parser-level ``max_nesting_depth``
        config (see ``ParseConfig``), which stops a deeply nested document from
        ever being built — and from exhausting the stack during parsing.
        ``limit_depth`` operates on an already-parsed AST.
    """

    def prune(node: Node, depth: int) -> Node:
        # Only descend through block containers; never into inline content.
        if not isinstance(node, _BLOCK_CHILD_NODES):
            return node
        is_container = isinstance(node, _DEPTH_CONTAINERS)
        cur = depth + 1 if is_container else depth
        children = getattr(node, "children", None)
        if not children:
            return node
        if is_container and cur >= max_depth:
            # This container is at the depth limit: keep it, drop nested content.
            return dataclasses.replace(node, children=())
        new_children = tuple(prune(c, cur) for c in children)
        return dataclasses.replace(node, children=new_children)

    def _policy(doc: Document) -> Document:
        # prune() preserves the node type it is given; the root is a Document,
        # so the result is too. assert keeps the static type precise.
        result = prune(doc, 0)
        assert isinstance(result, Document)
        return result

    return Policy(_policy)


# Pre-built policy sets.
#
# URL filtering uses an allow-list (allow_url_schemes) rather than a block-list:
# a block-list is bypassable by any novel dangerous scheme, whereas an allow-list
# only permits known-safe schemes (https/http/mailto) and scheme-less/relative
# URLs. Both reject obfuscated schemes (entity-encoded, embedded whitespace).
_safe_urls: Policy = allow_url_schemes()

llm_safe: Policy = strip_html | _safe_urls | normalize_unicode
web_safe: Policy = llm_safe  # Alias: same policy for web display of untrusted content
strict: Policy = strip_html | _safe_urls | normalize_unicode | strip_images | strip_raw_code


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
