"""GFM extended autolink scanning for Patitas.

Implements the GFM "Autolinks (extension)" feature: recognizing bare URLs,
``www.`` links, and bare email addresses inside ordinary inline text. This is
gated on ``ParseConfig.autolinks_enabled`` and is entirely separate from the
CommonMark angle-bracket autolinks (``<https://...>``) handled in
``special.py``, which work without any plugin.

Reference: https://github.github.com/gfm/#autolinks-extension-

The public entry point is :func:`scan_text_for_autolinks`, which takes a run of
plain text (and the character that immediately precedes it in the source) and
returns a list of inline tokens. Where it finds a valid autolink it emits a
``NodeToken`` wrapping a :class:`~patitas.nodes.Link`; everything else is
preserved as ``TextToken`` so behavior is byte-identical to plain text when no
autolink is present.

Thread Safety:
    Pure functions over their arguments; no shared mutable state. Safe for
    concurrent use.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from patitas.nodes import Link, Text
from patitas.parsing.inline.tokens import InlineToken, NodeToken, TextToken

if TYPE_CHECKING:
    from patitas.location import SourceLocation

# Characters that constitute a valid *left* boundary for a GFM autolink.
# Per the spec an autolink may only begin at start-of-line/text, after
# whitespace, or after one of these punctuation characters.
_BOUNDARY_CHARS = frozenset("*_~(")

# Trailing punctuation that is trimmed from the end of a matched URL/www link.
# ')' is handled separately (paren balancing); ';' is handled separately
# (entity-reference trimming).
_TRAILING_PUNCT = frozenset("?!.,:*_~")

# Characters allowed in an email local part (GFM extension).
_EMAIL_LOCAL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.+_-")

# Characters allowed within a single email domain segment (GFM extension).
_EMAIL_DOMAIN_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")


def _is_left_boundary(prev_char: str | None) -> bool:
    """Return True if *prev_char* is a valid left boundary for an autolink.

    A valid autolink is recognized only when preceded by start-of-line/text
    (``prev_char is None``), whitespace, or one of ``* _ ~ (``.
    """
    if prev_char is None:
        return True
    if prev_char.isspace():
        return True
    return prev_char in _BOUNDARY_CHARS


def _trim_trailing_punctuation(match: str) -> str:
    """Trim GFM trailing punctuation from a URL/www match.

    Rules (GFM autolinks extension):
    - Strip trailing ``?!.,:*_~`` characters.
    - A trailing ``)`` is stripped while there are more ``)`` than ``(`` in the
      remaining match.
    - If the match ends in a semicolon that closes an entity-like reference
      (``&...;``), strip the whole entity reference.

    These rules are applied repeatedly until the match is stable.
    """
    while match:
        before = match

        # Plain trailing punctuation.
        while match and match[-1] in _TRAILING_PUNCT:
            match = match[:-1]

        # Excess closing parens.
        while match and match[-1] == ")":
            opens = match.count("(")
            closes = match.count(")")
            if closes > opens:
                match = match[:-1]
            else:
                break

        # Entity-reference trailing ';' (e.g. trailing "&amp;").
        if match.endswith(";"):
            amp = match.rfind("&")
            if amp != -1:
                entity = match[amp + 1 : -1]
                # Entity body must be a (possibly numeric) reference name: only
                # letters/digits, or '#' + digits for numeric references.
                body = entity[1:] if entity.startswith("#") else entity
                if entity and body and all(ch.isalnum() for ch in body):
                    match = match[:amp]

        if match == before:
            break

    return match


def _scan_url(text: str, start: int, scheme_len: int) -> int:
    """Scan a bare ``http://``/``https://`` URL body starting at *start*.

    *start* points at the first character of the scheme. *scheme_len* is the
    length of the ``http://`` or ``https://`` prefix. Returns the exclusive end
    index of the raw match (before trailing-punctuation trimming), or *start*
    if the authority is not a valid domain.
    """
    text_len = len(text)
    authority_start = start + scheme_len

    # The authority runs until '/', '?', '#', whitespace, '<', or end.
    i = authority_start
    while i < text_len:
        c = text[i]
        if c.isspace() or c == "<" or c in "/?#":
            break
        i += 1
    authority = text[authority_start:i]

    # GFM: the authority must contain at least one '.' and be non-empty.
    if "." not in authority or not authority:
        return start

    # The rest of the link (path/query/fragment) runs until whitespace or '<'.
    while i < text_len:
        c = text[i]
        if c.isspace() or c == "<":
            break
        i += 1
    return i


def _scan_www(text: str, start: int) -> int:
    """Scan a ``www.`` link starting at *start* (the first ``w``).

    Returns the exclusive end index of the raw match, or *start* if the
    authority is not a valid domain.
    """
    text_len = len(text)

    # Authority runs until '/', '?', '#', whitespace, '<', or end.
    i = start
    while i < text_len:
        c = text[i]
        if c.isspace() or c == "<" or c in "/?#":
            break
        i += 1
    authority = text[start:i]

    # The authority must contain a dot beyond the leading "www." segment.
    rest = authority[4:]  # after "www."
    if not rest or "." not in authority:
        return start

    # Path/query/fragment until whitespace or '<'.
    while i < text_len:
        c = text[i]
        if c.isspace() or c == "<":
            break
        i += 1
    return i


def _scan_email(text: str, at_pos: int) -> tuple[int, int] | None:
    """Scan a bare email around the ``@`` at *at_pos*.

    Returns ``(start, end)`` of the matched email (exclusive end), or ``None``
    if there is no valid email. The local part is scanned backwards from the
    ``@``; the domain forwards.
    """
    text_len = len(text)

    # Scan local part backwards.
    local_end = at_pos
    i = at_pos - 1
    while i >= 0 and text[i] in _EMAIL_LOCAL_CHARS:
        i -= 1
    local_start = i + 1
    if local_start >= local_end:
        return None  # empty local part

    # Scan domain forwards: segments of [A-Za-z0-9-_] separated by '.'.
    j = at_pos + 1
    last_segment_end = -1
    saw_dot = False
    while j < text_len:
        seg_start = j
        while j < text_len and text[j] in _EMAIL_DOMAIN_CHARS:
            j += 1
        if j == seg_start:
            break  # empty segment
        last_segment_end = j
        if j < text_len and text[j] == ".":
            saw_dot = True
            j += 1
            continue
        break

    if last_segment_end == -1 or not saw_dot:
        return None  # need at least two segments (a dot in the domain)

    domain_end = last_segment_end

    # The last segment must not end in '-' or '_'.
    while domain_end > at_pos + 1 and text[domain_end - 1] in "-_":
        domain_end -= 1
    if domain_end <= at_pos + 1:
        return None

    return local_start, domain_end


def scan_text_for_autolinks(
    content: str,
    prev_char: str | None,
    location: SourceLocation,
) -> list[InlineToken]:
    """Split *content* into Text/Link tokens, recognizing GFM autolinks.

    Args:
        content: A run of plain text.
        prev_char: The character immediately preceding *content* in the source,
            or ``None`` if *content* starts the inline text. Used for the GFM
            left-boundary rule.
        location: Source location attached to produced nodes.

    Returns:
        A list of :class:`TextToken` / :class:`NodeToken` objects. When no
        autolink is found this is a single ``TextToken`` equal to *content*.
    """
    text_len = len(content)
    tokens: list[InlineToken] = []
    pos = 0
    emitted_start = 0  # start of pending plain-text run not yet flushed

    def flush_text(upto: int) -> None:
        if upto > emitted_start:
            tokens.append(TextToken(content=content[emitted_start:upto]))

    while pos < text_len:
        c = content[pos]

        # The character to the left of this candidate.
        left = content[pos - 1] if pos > 0 else prev_char

        matched_end = -1
        link_url: str | None = None
        link_text: str | None = None

        if (c == "h" or c == "H") and _is_left_boundary(left):
            lowered = content[pos : pos + 8].lower()
            scheme_len = 0
            if lowered.startswith("https://"):
                scheme_len = 8
            elif lowered.startswith("http://"):
                scheme_len = 7
            if scheme_len:
                raw_end = _scan_url(content, pos, scheme_len)
                if raw_end > pos:
                    match = content[pos:raw_end]
                    trimmed = _trim_trailing_punctuation(match)
                    if trimmed and "." in trimmed[scheme_len:]:
                        matched_end = pos + len(trimmed)
                        link_url = trimmed
                        link_text = trimmed

        if (
            matched_end == -1
            and (c == "w" or c == "W")
            and _is_left_boundary(left)
            and content[pos : pos + 4].lower() == "www."
        ):
            raw_end = _scan_www(content, pos)
            if raw_end > pos:
                match = content[pos:raw_end]
                trimmed = _trim_trailing_punctuation(match)
                if trimmed and "." in trimmed[4:]:
                    matched_end = pos + len(trimmed)
                    link_url = "http://" + trimmed
                    link_text = trimmed

        if matched_end == -1 and c == "@":
            email = _scan_email(content, pos)
            if email is not None:
                e_start, e_end = email
                # Apply the left-boundary rule to the start of the local part.
                e_left = content[e_start - 1] if e_start > 0 else prev_char
                if _is_left_boundary(e_left):
                    addr = content[e_start:e_end]
                    # Flush text up to the start of the local part (the local
                    # part chars were already absorbed into the pending run).
                    flush_text(e_start)
                    tokens.append(
                        NodeToken(
                            node=Link(
                                location=location,
                                url=f"mailto:{addr}",
                                title=None,
                                children=(Text(location=location, content=addr),),
                            )
                        )
                    )
                    pos = e_end
                    emitted_start = e_end
                    continue

        if matched_end != -1 and link_url is not None and link_text is not None:
            flush_text(pos)
            tokens.append(
                NodeToken(
                    node=Link(
                        location=location,
                        url=link_url,
                        title=None,
                        children=(Text(location=location, content=link_text),),
                    )
                )
            )
            pos = matched_end
            emitted_start = matched_end
            continue

        pos += 1

    flush_text(text_len)
    return tokens
