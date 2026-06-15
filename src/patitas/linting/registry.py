"""Lint rule registry for rule lookup and composition.

Clones the immutable-registry + mutable-builder structure from
``roles/registry.py`` verbatim: :class:`LintRuleRegistry` is immutable
(``__slots__`` + ``MappingProxyType``), built via :class:`LintRuleRegistryBuilder`
(``.register()`` chains, raising ``ValueError`` on duplicate ``rule_id`` and
``TypeError`` on missing metadata). :func:`create_default_lint_registry` builds
the three starter rules.

Thread Safety:
    ``LintRuleRegistry`` is immutable after creation (uses ``MappingProxyType``)
    and safe to share. Use ``LintRuleRegistryBuilder`` for mutable construction.

Example:
    >>> from patitas.linting import LintRuleRegistryBuilder, HeadingIncrementRule
    >>> builder = LintRuleRegistryBuilder()
    >>> builder.register(HeadingIncrementRule())
    LintRuleRegistryBuilder(...)
    >>> registry = builder.build()
    >>> registry.get("heading-increment") is not None
    True

"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from patitas.linting.protocol import LintRule


class LintRuleRegistry:
    """Immutable registry of lint rules keyed by ``rule_id``.

    Thread Safety:
        Truly immutable after creation (uses ``MappingProxyType``). Safe to
        share across threads.

    """

    __slots__ = ("_by_id", "_rules")

    _rules: tuple[LintRule, ...]
    _by_id: Mapping[str, LintRule]

    def __init__(self, rules: tuple[LintRule, ...], by_id: dict[str, LintRule]) -> None:
        """Initialize registry with pre-built mappings.

        Use :class:`LintRuleRegistryBuilder` to create instances.
        """
        self._rules = rules
        self._by_id = MappingProxyType(by_id)

    def get(self, rule_id: str) -> LintRule | None:
        """Get the rule registered under ``rule_id``, or None.

        Args:
            rule_id: Kebab-case rule id (e.g. "heading-increment").

        Returns:
            The rule if registered, None otherwise.

        """
        return self._by_id.get(rule_id)

    def has(self, rule_id: str) -> bool:
        """Check if ``rule_id`` is registered."""
        return rule_id in self._by_id

    @property
    def rules(self) -> tuple[LintRule, ...]:
        """Get all registered rules in registration order."""
        return self._rules

    def __contains__(self, rule_id: str) -> bool:
        """Support ``rule_id in registry`` syntax."""
        return self.has(rule_id)

    def __len__(self) -> int:
        """Number of registered rules."""
        return len(self._by_id)


class LintRuleRegistryBuilder:
    """Mutable builder for :class:`LintRuleRegistry`.

    Register rules, then call :meth:`build` to create an immutable registry.

    Example:
        >>> from patitas.linting import HeadingIncrementRule, NoEmptyLinkRule
        >>> builder = LintRuleRegistryBuilder()
        >>> builder.register(HeadingIncrementRule()).register(NoEmptyLinkRule())
        LintRuleRegistryBuilder(...)
        >>> registry = builder.build()

    """

    __slots__ = ("_by_id", "_rules")

    def __init__(self) -> None:
        """Initialize empty builder."""
        self._rules: list[LintRule] = []
        self._by_id: dict[str, LintRule] = {}

    def register(self, rule: LintRule) -> LintRuleRegistryBuilder:
        """Register a lint rule.

        Args:
            rule: Object implementing the :class:`LintRule` protocol.

        Returns:
            Self for chaining.

        Raises:
            TypeError: If ``rule`` lacks ``rule_id`` or ``default_severity``.
            ValueError: If a rule with the same ``rule_id`` is already
                registered.

        """
        if not hasattr(rule, "rule_id"):
            msg = f"Rule {type(rule).__name__} missing 'rule_id' attribute"
            raise TypeError(msg)

        if not hasattr(rule, "default_severity"):
            msg = f"Rule {type(rule).__name__} missing 'default_severity' attribute"
            raise TypeError(msg)

        rule_id = rule.rule_id
        if rule_id in self._by_id:
            existing = self._by_id[rule_id]
            msg = f"Rule '{rule_id}' already registered by {type(existing).__name__}"
            raise ValueError(msg)

        self._by_id[rule_id] = rule
        self._rules.append(rule)
        return self

    def register_all(self, rules: Iterable[LintRule]) -> LintRuleRegistryBuilder:
        """Register multiple rules.

        Args:
            rules: Iterable of rules to register.

        Returns:
            Self for chaining.

        """
        for rule in rules:
            self.register(rule)
        return self

    def build(self) -> LintRuleRegistry:
        """Build an immutable registry from the registered rules.

        Returns:
            An immutable :class:`LintRuleRegistry`.

        """
        return LintRuleRegistry(
            rules=tuple(self._rules),
            by_id=dict(self._by_id),
        )

    def __len__(self) -> int:
        """Number of registered rules."""
        return len(self._rules)


def create_default_lint_registry() -> LintRuleRegistry:
    """Create a registry with the three built-in starter rules.

    Prefixed to avoid the verified collision with directives' and roles'
    ``create_default_registry``. Rebuilds on each call (no shared mutable
    state); rules are stateless frozen singletons.

    Returns:
        A registry with ``heading-increment``, ``no-empty-link`` and
        ``trailing-whitespace``.

    """
    from patitas.linting.rules import (
        HeadingIncrementRule,
        NoEmptyLinkRule,
        TrailingWhitespaceRule,
    )

    builder = LintRuleRegistryBuilder()
    builder.register(HeadingIncrementRule())
    builder.register(NoEmptyLinkRule())
    builder.register(TrailingWhitespaceRule())
    return builder.build()
