"""Directive registry for handler lookup and registration.

The registry maps directive names to their handlers, enabling
extensibility and custom directive support.

Thread Safety:
DirectiveRegistry is immutable after creation. Safe to share.
Use DirectiveRegistryBuilder for mutable construction.

Example:
    >>> builder = DirectiveRegistryBuilder()
    >>> builder.register(NoteDirective())
    >>> builder.register(WarningDirective())
    >>> registry = builder.build()
    >>> handler = registry.get("note")
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from patitas.directives.protocol import DirectiveHandler


class DirectiveRegistry:
    """Immutable registry of directive handlers.

    Maps directive names to their handlers for lookup during parsing
    and rendering.

    Thread Safety:
        Immutable after creation. Safe to share across threads.
    """

    __slots__ = ("_handlers", "_by_name", "_by_token_type")

    def __init__(
        self,
        handlers: tuple[DirectiveHandler, ...],
        by_name: dict[str, DirectiveHandler],
        by_token_type: dict[str, DirectiveHandler],
    ) -> None:
        """Initialize registry with pre-built mappings.

        Use DirectiveRegistryBuilder to create instances.
        """
        self._handlers = handlers
        self._by_name = by_name
        self._by_token_type = by_token_type

    def get(self, name: str) -> DirectiveHandler | None:
        """Get handler for directive name.

        Args:
            name: Directive name (e.g., "note", "warning")

        Returns:
            Handler if registered, None otherwise
        """
        return self._by_name.get(name)

    def get_by_token_type(self, token_type: str) -> DirectiveHandler | None:
        """Get handler by token type.

        Args:
            token_type: Token type identifier (e.g., "admonition")

        Returns:
            Handler if registered, None otherwise
        """
        return self._by_token_type.get(token_type)

    def has(self, name: str) -> bool:
        """Check if directive name is registered."""
        return name in self._by_name

    @property
    def names(self) -> frozenset[str]:
        """Get all registered directive names."""
        return frozenset(self._by_name.keys())

    @property
    def handlers(self) -> tuple[DirectiveHandler, ...]:
        """Get all registered handlers."""
        return self._handlers

    def __contains__(self, name: str) -> bool:
        """Support 'name in registry' syntax."""
        return self.has(name)

    def __len__(self) -> int:
        """Number of registered directive names."""
        return len(self._by_name)


class DirectiveRegistryBuilder:
    """Mutable builder for DirectiveRegistry.

    Use this to register handlers, then call build() to create
    an immutable registry.

    Example:
        >>> builder = DirectiveRegistryBuilder()
        >>> builder.register(NoteDirective())
        >>> builder.register(WarningDirective())
        >>> registry = builder.build()
    """

    __slots__ = ("_handlers", "_by_name", "_by_token_type")

    def __init__(self) -> None:
        """Initialize empty builder."""
        self._handlers: list[DirectiveHandler] = []
        self._by_name: dict[str, DirectiveHandler] = {}
        self._by_token_type: dict[str, DirectiveHandler] = {}

    def register(self, handler: DirectiveHandler) -> DirectiveRegistryBuilder:
        """Register a directive handler.

        Args:
            handler: Handler implementing DirectiveHandler protocol

        Returns:
            Self for chaining

        Raises:
            ValueError: If handler name conflicts with existing registration
        """
        # Validate handler has required attributes
        if not hasattr(handler, "names"):
            msg = f"Handler {type(handler).__name__} missing 'names' attribute"
            raise TypeError(msg)

        if not hasattr(handler, "token_type"):
            msg = f"Handler {type(handler).__name__} missing 'token_type' attribute"
            raise TypeError(msg)

        # Register by all names
        for name in handler.names:
            if name in self._by_name:
                existing = self._by_name[name]
                msg = f"Directive '{name}' already registered by {type(existing).__name__}"
                raise ValueError(msg)
            self._by_name[name] = handler

        # Register by token type
        token_type = handler.token_type
        if token_type not in self._by_token_type:
            self._by_token_type[token_type] = handler

        self._handlers.append(handler)
        return self

    def register_all(self, handlers: list[DirectiveHandler]) -> DirectiveRegistryBuilder:
        """Register multiple handlers.

        Args:
            handlers: List of handlers to register

        Returns:
            Self for chaining
        """
        for handler in handlers:
            self.register(handler)
        return self

    def build(self) -> DirectiveRegistry:
        """Build immutable registry from registered handlers.

        Returns:
            Immutable DirectiveRegistry
        """
        return DirectiveRegistry(
            handlers=tuple(self._handlers),
            by_name=dict(self._by_name),
            by_token_type=dict(self._by_token_type),
        )

    def __len__(self) -> int:
        """Number of registered handlers."""
        return len(self._handlers)


def _build_default_registry() -> DirectiveRegistry:
    """Build the default registry (internal, not cached)."""
    from patitas.directives.builtins.admonition import AdmonitionDirective
    from patitas.directives.builtins.container import ContainerDirective
    from patitas.directives.builtins.dropdown import DropdownDirective
    from patitas.directives.builtins.tabs import TabItemDirective, TabSetDirective

    builder = DirectiveRegistryBuilder()

    # Core directives
    builder.register(AdmonitionDirective())
    builder.register(ContainerDirective())
    builder.register(DropdownDirective())

    # Tabs
    builder.register(TabSetDirective())
    builder.register(TabItemDirective())

    return builder.build()


# Cached singleton — thread-safe since DirectiveRegistry is immutable
_DEFAULT_REGISTRY: DirectiveRegistry | None = None


def create_default_registry() -> DirectiveRegistry:
    """Get the default directive registry (cached singleton).

    Returns:
        Registry with portable directives:
        - Admonitions: note, warning, tip, danger, etc.
        - Tabs: tab-set, tab-item
        - Dropdown: collapsible content
        - Container: generic wrapper

    Thread Safety:
        Returns a cached immutable registry. Safe for concurrent access.

    Note:
        Bengal-specific directives (cards, code-tabs, navigation, etc.)
        are registered separately via patitas[bengal].
    """
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = _build_default_registry()
    return _DEFAULT_REGISTRY


def create_registry_with_defaults() -> DirectiveRegistryBuilder:
    """Create a builder pre-populated with default directives.

    Use this to extend the default set with custom directives:

        >>> builder = create_registry_with_defaults()
        >>> builder.register(MyCustomDirective())
        >>> registry = builder.build()

    Returns:
        DirectiveRegistryBuilder with defaults already registered
    """
    from patitas.directives.builtins.admonition import AdmonitionDirective
    from patitas.directives.builtins.container import ContainerDirective
    from patitas.directives.builtins.dropdown import DropdownDirective
    from patitas.directives.builtins.tabs import TabItemDirective, TabSetDirective

    builder = DirectiveRegistryBuilder()

    # Core directives
    builder.register(AdmonitionDirective())
    builder.register(ContainerDirective())
    builder.register(DropdownDirective())

    # Tabs
    builder.register(TabSetDirective())
    builder.register(TabItemDirective())

    return builder
