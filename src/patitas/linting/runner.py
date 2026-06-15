"""The lint() entrypoint and the Linter class.

:func:`lint` is the headline function (symmetric with ``parse``/``render``). It
accepts a ``str`` (parsed internally, capturing the source for line rules) OR a
pre-parsed :class:`~patitas.nodes.Document` (with the raw source supplied via the
keyword-only ``text`` parameter). One :class:`~patitas.linting.context.LintContext`
is built and fed to each rule's ``check`` once; the runner STAMPS each
diagnostic's ``rule_id`` and ``severity`` from the emitting rule, then returns a
deterministically sorted list.

Thread Safety:
    No module-level mutable state. The only mutable state is the per-call
    accumulator list and the per-construction ``_NodeCollector`` inside the
    context — both created fresh per call. A single :class:`Linter` (immutable
    registry on ``__slots__``) is safe to share across threads.

"""

from __future__ import annotations

from typing import TYPE_CHECKING

from patitas.linting.context import LintContext
from patitas.linting.diagnostic import Diagnostic
from patitas.linting.registry import LintRuleRegistry, create_default_lint_registry
from patitas.nodes import Document

if TYPE_CHECKING:
    from collections.abc import Sequence

    from patitas.linting.protocol import LintRule


def _resolve_rules(
    rules: Sequence[LintRule] | LintRuleRegistry | None,
) -> tuple[LintRule, ...]:
    """Normalize the ``rules`` argument to a tuple of rules in order."""
    if rules is None:
        return create_default_lint_registry().rules
    if isinstance(rules, LintRuleRegistry):
        return rules.rules
    return tuple(rules)


def _run(ctx: LintContext, rules: tuple[LintRule, ...]) -> list[Diagnostic]:
    """Run rules over a context, stamping id/severity, sorted for determinism."""
    diagnostics: list[Diagnostic] = []
    for rule in rules:
        # Stamp rule_id and severity from the emitting rule so they can never
        # drift from the producing rule's class metadata.
        diagnostics.extend(
            Diagnostic(
                rule_id=rule.rule_id,
                message=diag.message,
                location=diag.location,
                severity=rule.default_severity,
            )
            for diag in rule.check(ctx)
        )

    diagnostics.sort(
        key=lambda d: (
            d.location.offset,
            d.location.lineno,
            d.location.col_offset,
            d.rule_id,
        )
    )
    return diagnostics


def lint(
    source: str | Document,
    *,
    text: str = "",
    source_file: str | None = None,
    rules: Sequence[LintRule] | LintRuleRegistry | None = None,
) -> list[Diagnostic]:
    """Lint Markdown and return a list of diagnostics.

    Pass a ``str`` for the trivial path: it is parsed internally and the same
    string is used as the raw source for line-oriented rules, so all rules run
    with zero ceremony. Pass a pre-parsed :class:`~patitas.nodes.Document` for
    the power path, supplying the raw source via ``text=`` so source-driven
    rules (e.g. trailing-whitespace) are not silently skipped.

    Args:
        source: Markdown source string, or a pre-parsed ``Document``.
        text: Raw source for a pre-parsed ``Document``. Ignored when ``source``
            is a ``str``. If omitted for a ``Document``, source-driven rules
            have no input and emit nothing (AST rules still run).
        source_file: Optional source file path; flows into the parse and into
            synthesized diagnostic locations.
        rules: An explicit ``Sequence[LintRule]`` (used in order), a
            :class:`LintRuleRegistry` (uses ``registry.rules``), or None (the
            three built-in starter rules).

    Returns:
        A materialized list of :class:`Diagnostic`, sorted by
        ``(offset, lineno, col_offset, rule_id)``.

    Example:
        >>> from patitas import lint
        >>> diags = lint("# H1\\n\\n### H3   ")
        >>> [d.rule_id for d in diags]
        ['trailing-whitespace', 'heading-increment']

    """
    from patitas import parse  # local import to avoid an import cycle

    if isinstance(source, Document):
        document = source
        raw_source = text
    else:
        document = parse(source, source_file=source_file)
        raw_source = source

    ctx = LintContext(document=document, source=raw_source, source_file=source_file)
    return _run(ctx, _resolve_rules(rules))


class Linter:
    """Reusable linter bound to an immutable rule registry.

    Use this to lint many documents with a fixed rule set. The registry is held
    immutably on ``__slots__``; each :meth:`lint` call builds its own context
    and accumulator, so one ``Linter`` is safe to share across threads.

    """

    __slots__ = ("_registry",)

    def __init__(self, registry: LintRuleRegistry | None = None) -> None:
        """Initialize with a registry (the default starter rules if None).

        Args:
            registry: An immutable :class:`LintRuleRegistry`. Defaults to
                :func:`create_default_lint_registry`.

        """
        self._registry = registry if registry is not None else create_default_lint_registry()

    def lint(
        self,
        source: str | Document,
        *,
        text: str = "",
        source_file: str | None = None,
    ) -> list[Diagnostic]:
        """Lint Markdown using this linter's registry.

        Same polymorphic signature as the top-level :func:`lint`, minus the
        ``rules`` argument (the registry is fixed at construction).

        Args:
            source: Markdown source string, or a pre-parsed ``Document``.
            text: Raw source for a pre-parsed ``Document`` (see :func:`lint`).
            source_file: Optional source file path.

        Returns:
            A sorted list of :class:`Diagnostic`.

        """
        return lint(source, text=text, source_file=source_file, rules=self._registry)
