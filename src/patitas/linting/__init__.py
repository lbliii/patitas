"""Content linting for Patitas — a ruff-for-Markdown over the typed AST.

Lint rules are stateless objects implementing the :class:`LintRule` protocol.
Each receives one immutable :class:`LintContext` (the parsed Document, the raw
source, and a precomputed document-order node sequence) and yields
:class:`Diagnostic` objects that reuse the existing ``SourceLocation``.

The headline entrypoint is :func:`lint`, which accepts either a Markdown string
(parsed internally) or a pre-parsed Document plus its raw source.

Thread Safety:
    Rules are stateless and the runner is created fresh per :func:`lint` call,
    so one :class:`Linter` (or one :class:`LintRuleRegistry`) is safe to share
    across threads.

Example:
    >>> from patitas import lint, Diagnostic
    >>> from patitas.linting import LintRule, Severity, LintContext, LintRuleRegistryBuilder
    >>> diags = lint("# Title\\n\\n### Skipped   ")
    >>> sorted({d.rule_id for d in diags})
    ['heading-increment', 'trailing-whitespace']

"""

from patitas.linting.context import LintContext
from patitas.linting.diagnostic import Diagnostic, Severity
from patitas.linting.protocol import LintRule
from patitas.linting.registry import (
    LintRuleRegistry,
    LintRuleRegistryBuilder,
    create_default_lint_registry,
)
from patitas.linting.rules import (
    HeadingIncrementRule,
    NoEmptyLinkRule,
    TrailingWhitespaceRule,
)
from patitas.linting.runner import Linter, lint

__all__ = [  # noqa: RUF022 — grouped by category for maintainability
    # Core data types
    "Diagnostic",
    "Severity",
    "LintContext",
    # Protocol
    "LintRule",
    # Entrypoints
    "lint",
    "Linter",
    # Registry
    "LintRuleRegistry",
    "LintRuleRegistryBuilder",
    "create_default_lint_registry",
    # Starter rules
    "HeadingIncrementRule",
    "NoEmptyLinkRule",
    "TrailingWhitespaceRule",
]
