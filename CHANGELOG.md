# Changelog

All notable changes to Patitas will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Incremental re-parsing** — `parse_incremental(new_source, previous, edit_start,
  edit_end, new_length)` accepts a previous AST and an edit range, identifies which
  top-level blocks overlap the edit, re-parses only that region, and splices new blocks
  back into the existing AST. Unaffected blocks are reused with adjusted offsets. Cost
  is O(change) rather than O(document). Falls back to full re-parse on failure.
  Exported from `patitas.incremental` and `patitas` top-level.

## [0.1.1] - 2026-01-13

### Added

- **`Parser._reinit()`** — Reinitialize parser for reuse, enabling instance pooling in frameworks like Bengal. Resets all per-parse state while keeping the instance allocated, reducing allocation overhead for high-volume parsing.

- **`ParseConfig.from_dict()`** — Create ParseConfig from dictionary, useful for framework integration where config may come from external sources.

## [0.1.0] - 2026-01-12

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

### Changed

- **`DelimiterToken`** — Renamed `count` attribute to `run_length` for clarity (vs Bengal's embedded version).

[Unreleased]: https://github.com/lbliii/patitas/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/lbliii/patitas/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lbliii/patitas/releases/tag/v0.1.0
