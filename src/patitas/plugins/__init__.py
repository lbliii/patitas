"""Plugin system for Patitas Markdown parser.

Plugins extend Patitas with additional syntax support:
- table: GFM-style pipe tables
- strikethrough: ~~deleted~~ syntax
- task_lists: - [ ] checkboxes (built into core, enabled by default)
- footnotes: [^1] references
- math: $inline$ and $$block$$ math
- autolinks: Automatic URL and email detection

Usage:
    >>> from patitas import Markdown
    >>>
    >>> # Enable specific plugins
    >>> md = Markdown(plugins=["table", "strikethrough", "math"])
    >>> html = md("| A | B |\n|---|---|\n| 1 | 2 |")
    >>>
    >>> # Enable all plugins
    >>> md = Markdown(plugins=["all"])

Plugin Architecture:
Unlike mistune's regex-based plugins, Patitas uses a state-machine lexer.
Plugins hook into specific extension points:

1. Inline plugins (strikethrough, math inline):
   - Registered with the inline parser
   - Called when special characters are encountered

2. Block plugins (table, math block, footnote definitions):
   - Registered with the block scanner
   - Called at line start when block patterns match

3. Post-processing plugins (footnotes, autolinks):
   - Transform AST or rendered output
   - Called after main parsing/rendering

Thread Safety:
All plugins are stateless. State is stored in AST nodes or passed as arguments.
Multiple threads can use the same plugin instances concurrently.

"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from patitas.lexer import Lexer
    from patitas.parser import Parser
    from patitas.renderers.html import HtmlRenderer

# These imports are kept for backward compatibility in apply_plugins signature

__all__ = [
    "PatitasPlugin",
    "BUILTIN_PLUGINS",
    "get_plugin",
    "apply_plugins",
]


@runtime_checkable
class PatitasPlugin(Protocol):
    """Protocol for Patitas plugins.

    Plugins are lightweight markers that enable features in Patitas.
    The actual parsing behavior is controlled by ParseConfig via ContextVars.

    To enable a plugin, pass its name to Markdown(plugins=[...]).
    The Markdown class reads the plugin names and sets the appropriate
    ParseConfig flags.

    Thread Safety:
        Plugins must be stateless. All state should be in AST nodes.

    """

    @property
    def name(self) -> str:
        """Plugin identifier."""
        ...


# Registry of built-in plugins
BUILTIN_PLUGINS: dict[str, type[PatitasPlugin]] = {}


from collections.abc import Callable


def register_plugin(
    name: str,
) -> Callable[[type[PatitasPlugin]], type[PatitasPlugin]]:
    """Decorator to register a plugin.

    Args:
        name: Plugin name for lookup

    Returns:
        Decorator function that registers and returns the class

    Usage:
        @register_plugin("table")
        class TablePlugin:
                ...

    """

    def decorator(cls: type[PatitasPlugin]) -> type[PatitasPlugin]:
        BUILTIN_PLUGINS[name] = cls
        return cls

    return decorator


def get_plugin(name: str) -> PatitasPlugin:
    """Get a plugin instance by name.

    Args:
        name: Plugin name (e.g., "table", "strikethrough")

    Returns:
        Plugin instance

    Raises:
        KeyError: If plugin name is not recognized

    """
    if name not in BUILTIN_PLUGINS:
        available = ", ".join(sorted(BUILTIN_PLUGINS.keys()))
        raise KeyError(f"Unknown plugin: {name!r}. Available: {available}")
    return BUILTIN_PLUGINS[name]()


def apply_plugins(
    plugins: list[str],
    lexer_class: type[Lexer],
    parser_class: type[Parser],
    renderer_class: type[HtmlRenderer],
) -> None:
    """Apply plugins to parser components.

    Note: This function is deprecated. Plugin configuration is now handled
    by the Markdown class via ParseConfig and ContextVars. This function
    is kept for backward compatibility but no longer does anything.

    Args:
        plugins: List of plugin names to apply
        lexer_class: Lexer class to extend (unused)
        parser_class: Parser class to extend (unused)
        renderer_class: Renderer class to extend (unused)

    """
    # Configuration is now handled via ParseConfig/ContextVars
    # This function is a no-op for backward compatibility
    pass


# Import built-in plugins to register them
# These imports trigger the @register_plugin decorators
from patitas.plugins.autolinks import AutolinksPlugin  # noqa: E402
from patitas.plugins.footnotes import FootnotesPlugin  # noqa: E402
from patitas.plugins.math import MathPlugin  # noqa: E402
from patitas.plugins.strikethrough import StrikethroughPlugin  # noqa: E402
from patitas.plugins.table import TablePlugin  # noqa: E402
from patitas.plugins.task_lists import TaskListPlugin  # noqa: E402

__all__ += [
    "StrikethroughPlugin",
    "TablePlugin",
    "MathPlugin",
    "TaskListPlugin",
    "FootnotesPlugin",
    "AutolinksPlugin",
]
