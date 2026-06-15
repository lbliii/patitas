"""The three starter lint rules for issue #56 Phase-1.

Each rule is a stateless ``@dataclass(frozen=True, slots=True)`` implementing
the :class:`~patitas.linting.protocol.LintRule` protocol. All per-run state lives
in local variables inside ``check`` — nothing is stored on the rule instance —
so a single rule instance is safe to share across threads.

Thread Safety:
    All rules are stateless frozen dataclasses. ``check`` holds only local
    state. Safe to call concurrently.

"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from patitas.linting.diagnostic import Diagnostic, Severity
from patitas.location import SourceLocation
from patitas.nodes import (
    CodeSpan,
    FencedCode,
    Image,
    IndentedCode,
    Link,
    Node,
    Text,
)

if TYPE_CHECKING:
    from patitas.linting.context import LintContext


@dataclass(frozen=True, slots=True)
class HeadingIncrementRule:
    """Flag headings that skip a level (e.g. h1 -> h3).

    Mirrors markdownlint MD001. Operates on the flat, document-order sequence of
    all headings (including nested ones) from ``ctx.headings()``, comparing each
    heading to its immediate predecessor. The first heading is never flagged and
    may start at any level; only an upward jump of more than one is a violation.

    """

    rule_id: ClassVar[str] = "heading-increment"
    default_severity: ClassVar[Severity] = Severity.WARNING

    def check(self, ctx: LintContext) -> Iterable[Diagnostic]:
        """Yield a diagnostic for each heading that skips a level."""
        prev_level: int | None = None
        for heading in ctx.headings():
            level = heading.level
            if prev_level is not None and level > prev_level + 1:
                expected = prev_level + 1
                yield Diagnostic(
                    rule_id=self.rule_id,
                    message=(
                        f"Heading level skipped: expected h{expected} or lower "
                        f"after h{prev_level}, found h{level}"
                    ),
                    location=heading.location,
                    severity=self.default_severity,
                )
            prev_level = level


def _has_visible_content(node: Node) -> bool:
    """Return True if ``node`` (or any descendant) renders visible content.

    Visible content is any non-whitespace ``Text``; any ``Image`` (a visible,
    clickable target); a ``CodeSpan`` with non-empty code; or non-whitespace
    inline HTML. Recurses through emphasis/strong/strikethrough/link wrappers
    that carry a ``children`` tuple.
    """
    match node:
        case Text(content=content):
            return bool(content.strip())
        case Image():
            return True
        case CodeSpan(code=code):
            return bool(code.strip())
        case _:
            children = getattr(node, "children", None)
            html = getattr(node, "html", None)
            if isinstance(html, str) and html.strip():
                return True
            if isinstance(children, tuple):
                return any(_has_visible_content(child) for child in children)
            return False


@dataclass(frozen=True, slots=True)
class NoEmptyLinkRule:
    """Flag links with no visible text.

    A link is empty when it has no children OR all descendant content is
    whitespace-only. An ``Image`` descendant, a non-empty ``CodeSpan``, or
    non-whitespace inline HTML counts as visible content, so icon links and
    code links are not flagged. ``Image`` nodes themselves are never inspected
    (``Image.alt`` is a flat string; ``Image`` is not a ``Link``).

    Inline nodes share the enclosing block's location, so the diagnostic is
    reported at the start of the enclosing block; the url is included in the
    message to disambiguate multiple empty links within one block.

    """

    rule_id: ClassVar[str] = "no-empty-link"
    default_severity: ClassVar[Severity] = Severity.WARNING

    def check(self, ctx: LintContext) -> Iterable[Diagnostic]:
        """Yield a diagnostic for each link with no visible text."""
        for link in ctx.nodes_of_type(Link):
            if not any(_has_visible_content(child) for child in link.children):
                yield Diagnostic(
                    rule_id=self.rule_id,
                    message=f"Link has no visible text (url: {link.url!r})",
                    location=link.location,
                    severity=self.default_severity,
                )


@dataclass(frozen=True, slots=True)
class TrailingWhitespaceRule:
    """Flag source lines ending in space/tab, excluding code-block content.

    A pure source scan over ``ctx.lines`` (source split on ``"\\n"``). Lines
    inside a top-level fenced or indented code block are skipped, since trailing
    whitespace there is legitimate code content (this keeps the repo's own docs
    clean when dogfooded). The whitespace signal is unrecoverable from the AST
    (trailing spaces are stripped during parsing), so it is detected from raw
    source; the code-block ranges are read from the AST.

    Hard-line-break lines (exactly two trailing spaces) are still flagged — at
    INFO severity, matching markdownlint MD009's default — so they never trip a
    default error-only CLI exit code.

    """

    rule_id: ClassVar[str] = "trailing-whitespace"
    default_severity: ClassVar[Severity] = Severity.INFO

    def check(self, ctx: LintContext) -> Iterable[Diagnostic]:
        """Yield a diagnostic for each line with trailing whitespace."""
        skip = self._code_block_lines(ctx)
        for index, raw_line in enumerate(ctx.lines):
            lineno = index + 1
            if lineno in skip:
                continue
            # Treat a trailing CR (CRLF input after split('\n')) as part of the
            # line boundary, not as content.
            line = raw_line[:-1] if raw_line.endswith("\r") else raw_line
            stripped = line.rstrip(" \t")
            if stripped == line:
                continue
            count = len(line) - len(stripped)
            yield Diagnostic(
                rule_id=self.rule_id,
                message=f"Trailing whitespace ({count} character(s))",
                location=SourceLocation(
                    lineno=lineno,
                    col_offset=len(stripped) + 1,
                    source_file=ctx.source_file,
                ),
                severity=self.default_severity,
            )

    @staticmethod
    def _code_block_lines(ctx: LintContext) -> frozenset[int]:
        """Compute the set of 1-indexed line numbers inside top-level code.

        The parser fixes ``location.end_lineno`` at ``lineno + 1`` for both
        ``FencedCode`` and ``IndentedCode`` regardless of the block's real
        length, so it cannot be used to derive the span. Instead the true span
        is recovered from data already on each node:

        * ``FencedCode`` (top-level): the opening fence is ``location.lineno``
          and ``source_end`` (a byte offset into ``ctx.source``) maps to the
          closing fence line, so the inclusive span is ``location.lineno`` ..
          ``source[:source_end].count("\\n") + 1``. Nested fences carry a
          ``content_override`` and source offsets relative to a sub-parser, so
          they fall back to the location span (best-effort, as documented).
        * ``IndentedCode``: ``code.count("\\n")`` gives the number of line
          breaks; the inclusive end is ``location.lineno + count`` less one if
          ``code`` ends in a trailing newline.

        Nested code blocks may carry inner-buffer relative line numbers, so
        exclusion is best-effort for top-level code.
        """
        skip: set[int] = set()
        source = ctx.source
        for fenced in ctx.nodes_of_type(FencedCode):
            start = fenced.location.lineno
            if fenced.content_override is None:
                # Top-level: source_end maps to the closing-fence (or final
                # content) line; this captures opening fence + content + close.
                end = source[: fenced.source_end].count("\n") + 1
            else:
                # Nested: source offsets are sub-parser relative; fall back.
                loc = fenced.location
                end = loc.end_lineno if loc.end_lineno is not None else start
            skip.update(range(start, max(start, end) + 1))
        for indented in ctx.nodes_of_type(IndentedCode):
            start = indented.location.lineno
            code = indented.code
            end = start + code.count("\n") - (1 if code.endswith("\n") else 0)
            skip.update(range(start, max(start, end) + 1))
        return frozenset(skip)
