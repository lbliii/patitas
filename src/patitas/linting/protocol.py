"""LintRule protocol — the single contract a rule author implements.

A rule is a stateless, pure object: it receives one immutable
:class:`~patitas.linting.context.LintContext` and yields
:class:`~patitas.linting.diagnostic.Diagnostic` objects. Mirrors the
``RoleHandler``/``DirectiveHandler`` protocol style (``@runtime_checkable``,
``ClassVar`` metadata with per-attribute docstrings, ``...`` method body, and
Args/Returns/Thread Safety docstring sections).

Thread Safety:
    Rules MUST be stateless. The same rule instance may be invoked concurrently
    from multiple threads against different documents.

"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from patitas.linting.context import LintContext
    from patitas.linting.diagnostic import Diagnostic, Severity


@runtime_checkable
class LintRule(Protocol):
    """Protocol for a single, stateless Markdown lint rule.

    Implement this protocol to add a custom rule. A rule is pure: it
    receives an immutable :class:`LintContext` (the parsed Document plus
    the raw source and a precomputed document-order node sequence) and
    yields :class:`Diagnostic` objects. Rules never mutate the AST, the
    context, or any shared state, and they never see the runner.

    AST-oriented rules read ``ctx.document`` / ``ctx.headings()`` /
    ``ctx.nodes_of_type(...)``; line-oriented rules read ``ctx.lines``.
    One method serves both: the rule reads whatever it needs.

    Attributes:
        rule_id: Unique, kebab-case rule identifier (e.g.
            "heading-increment"). Used as the registry key and stamped onto
            every Diagnostic this rule emits.
        default_severity: Severity stamped onto Diagnostics this rule emits.

    Thread Safety:
        Rules MUST be stateless. All per-run state must live in local
        variables inside ``check`` or in the immutable LintContext. The
        same rule instance may be invoked concurrently from multiple
        threads against different documents.

    Example:
        >>> from dataclasses import dataclass
        >>> from typing import ClassVar
        >>> from patitas.linting import Diagnostic, Severity
        >>> from patitas.location import SourceLocation
        >>> @dataclass(frozen=True, slots=True)
        ... class NoTabsRule:
        ...     rule_id: ClassVar[str] = "no-tabs"
        ...     default_severity: ClassVar[Severity] = Severity.WARNING
        ...     def check(self, ctx):
        ...         for i, line in enumerate(ctx.lines, start=1):
        ...             col = line.find("\\t")
        ...             if col != -1:
        ...                 yield Diagnostic(
        ...                     rule_id=self.rule_id,
        ...                     message="Line contains a tab character",
        ...                     location=SourceLocation(
        ...                         lineno=i, col_offset=col + 1,
        ...                         source_file=ctx.source_file),
        ...                     severity=self.default_severity,
        ...                 )

    """

    rule_id: ClassVar[str]
    """Unique kebab-case rule id; the registry key and the value stamped into Diagnostics."""

    default_severity: ClassVar[Severity]
    """Severity stamped onto Diagnostics emitted by this rule."""

    def check(self, ctx: LintContext) -> Iterable[Diagnostic]:
        """Inspect the document/source and yield diagnostics.

        Called exactly once per lint run. AST rules read ``ctx.document``,
        ``ctx.headings()`` or ``ctx.nodes_of_type(...)`` (a precomputed,
        document-order node sequence — rules never subclass BaseVisitor and
        never depend on traversal-hook timing). Line-oriented rules read
        ``ctx.lines`` (source split on '\\n').

        Args:
            ctx: Immutable lint context carrying the parsed Document
                (``ctx.document``), the raw source (``ctx.source`` /
                ``ctx.lines``), ``ctx.source_file``, and precomputed node
                accessors.

        Returns:
            An iterable of Diagnostic (may be a generator). The runner
            stamps ``rule_id`` and ``severity`` from this rule, so a rule
            need not get those exactly right, but should set
            ``message`` and ``location``. AST rules should reuse a node's
            ``location``; line rules synthesize their own.

        Thread Safety:
            Must not modify any shared state. May be called concurrently.

        """
        ...
