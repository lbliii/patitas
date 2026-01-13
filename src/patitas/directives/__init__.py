"""Directive system for Patitas.

Provides MyST-style fenced directives: :::{name} title

This module is part of the core package and provides the base
infrastructure for directive parsing and options handling.

Usage:
    from patitas.directives import DirectiveOptions

See patitas[directives] extra for portable built-in directives.
"""

from __future__ import annotations

from patitas.directives.options import (
    AdmonitionOptions,
    CodeBlockOptions,
    DirectiveOptions,
    FigureOptions,
    ImageOptions,
    StyledOptions,
    TabItemOptions,
    TabSetOptions,
)

__all__ = [
    "DirectiveOptions",
    "StyledOptions",
    "AdmonitionOptions",
    "CodeBlockOptions",
    "ImageOptions",
    "FigureOptions",
    "TabSetOptions",
    "TabItemOptions",
]
