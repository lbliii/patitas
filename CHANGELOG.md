# Changelog

All notable changes to Patitas will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial extraction from Bengal's embedded parser
- Core Markdown parser with CommonMark 0.31.2 compliance (652 examples)
- Zero-copy lexer with O(n) guaranteed parsing
- Typed AST with frozen dataclasses
- StringBuilder for O(n) rendering
- Plugin system: tables, footnotes, math, strikethrough, task lists
- Directive system with MyST-style fenced syntax
- Role system for inline extensions
- Free-threading support (Python 3.14t ready)

### Installation Tiers

- `patitas` — Core parser (zero dependencies)
- `patitas[directives]` — Portable directives (admonition, dropdown, tabs)
- `patitas[syntax]` — Syntax highlighting via Rosettes
- `patitas[bengal]` — Full Bengal directive suite

## [0.1.0] - 2026-01-12

### Added

- First public release
- Extracted from Bengal v0.1.8

[Unreleased]: https://github.com/lbliii/patitas/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lbliii/patitas/releases/tag/v0.1.0
