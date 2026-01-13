"""Built-in directive handlers for Patitas.

Provides commonly-used directives out of the box:
- Admonitions: note, warning, tip, danger, error, info, example, success, caution, seealso
- Dropdown: collapsible content with icons, badges, colors
- Tabs: tab-set and tab-item with sync and CSS state machine modes
- Container: generic wrapper div with custom classes
"""

from __future__ import annotations

from patitas.directives.builtins.admonition import AdmonitionDirective
from patitas.directives.builtins.container import ContainerDirective
from patitas.directives.builtins.dropdown import DropdownDirective
from patitas.directives.builtins.tabs import TabItemDirective, TabSetDirective

__all__ = [
    # Admonitions
    "AdmonitionDirective",
    # Container
    "ContainerDirective",
    # Dropdown
    "DropdownDirective",
    # Tabs
    "TabItemDirective",
    "TabSetDirective",
]
