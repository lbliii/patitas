"""Built-in role handlers.

Provides commonly-used roles out of the box:
- ref: Cross-references
- doc: Document links
- kbd: Keyboard shortcuts
- abbr: Abbreviations with expansion
- math: Inline math
- sub: Subscript
- sup: Superscript
- icon: Inline SVG icons

"""

from patitas.roles.builtins.formatting import (
    AbbrRole,
    KbdRole,
    SubRole,
    SupRole,
)
from patitas.roles.builtins.icons import IconRole
from patitas.roles.builtins.math import MathRole
from patitas.roles.builtins.reference import DocRole, RefRole

__all__ = [
    "RefRole",
    "DocRole",
    "KbdRole",
    "AbbrRole",
    "MathRole",
    "SubRole",
    "SupRole",
    "IconRole",
]
