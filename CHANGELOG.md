# Changelog

All notable changes to Patitas will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.3] - 2026-03-01

### Added

- **Frontmatter parsing** — `parse_frontmatter(content)` and `extract_body(content)` for
  YAML frontmatter extraction. `parse_frontmatter` returns `(metadata, body_markdown)`;
  complementary to `parse_notebook(content) -> (markdown_content, metadata)`. Handles
  valid frontmatter, missing/unclosed delimiters, and invalid YAML (graceful degradation).
  Normalizes `weight`, `order`, `priority` to float for SSG cascade/sort. Exported from
  `patitas.frontmatter` and `patitas` top-level.

### Changed

- **Dependencies** — Added `pyyaml>=6.0` as core dependency for frontmatter support.

## [0.3.2] - 2026-03-01

### Added

- **LLM renderer** — `render_llm(doc, source?)` and `LlmRenderer` for structured plain text
  output for model consumption. No HTML; markdown-like labels for code (`[code:lang]`),
  math (`[math] ... [/math]`), images (`[image: alt]`). Skips HtmlBlock and HtmlInline for
  safety. Exported from `patitas.renderers.llm` and `patitas` top-level.

- **Sanitization** — `sanitize(doc, policy)` and composable `Policy` instances. Strip HTML,
  dangerous URLs (javascript:, data:, vbscript:), zero-width/bidi characters (Trojan Source
  mitigation), images, raw code. Pre-built policies: `llm_safe`, `web_safe` (alias for llm_safe), `strict`.
  Compose via `|` operator. Exported from `patitas.sanitize` and `patitas` top-level.

- **`extract_text(node, source?)`** — Extract plain text from any AST node. Skips
  HtmlBlock/HtmlInline. Used for heading slugs, excerpts, LLM-safe rendering. Exported
  from `patitas.text` and `patitas` top-level.

- **LLM safety example** — `examples/llm_safety/llm_safe_context.py` demonstrates
  parse → sanitize → render_llm pipeline for RAG/retrieval contexts.

- **Parallel benchmark** — `benchmarks/benchmark_parallel.py` for free-threading scaling
  demo. Near-linear speedup on multi-core (e.g. 6.6x on 8 threads).

### Changed

- **README** — Updated free-threading wording and parallel benchmark example.
- **Ruff** — Dev dependency bumped to `>=0.15.1` (fixes except-parenthesis bug with PEP 758).

## [0.3.1] - 2026-02-15

### Added

- **Parse cache** — Content-addressed `(content_hash, config_hash) -> Document` cache.
  `parse()`, `Markdown.parse()`, and `Markdown.parse_many()` accept optional `cache:
  ParseCache | None`. `DictParseCache` for in-memory use; `hash_content()` and
  `hash_config()` for key computation. Enables faster incremental builds (undo/revert,
  duplicate content). Exported from `patitas.cache` and `patitas` top-level.

- **`examples/`** — Runnable examples showcasing Patitas: basic (hello, Markdown class),
  notebooks (parse_notebook), AST (visitor, transform), directives (builtin, custom),
  incremental, differ, plugins (math, tables, footnotes), advanced (parallel parse,
  serialize). Run with `python examples/basic/hello_markdown.py` etc.

- **Excerpt support** — `extract_excerpt(ast, source, ...)` and `extract_meta_description(ast,
  source)` for structurally correct excerpt extraction from AST. Stops at block boundaries;
  optional plain text or HTML output. Useful for list previews, meta descriptions, search
  snippets. Exported from `patitas.excerpt` and `patitas` top-level.

### Fixed

- **`@directive` decorator** — `parse()` now accepts `options` kwarg (was `opts`), matching
  parser invocation and fixing custom directive registration.

## [0.3.0] - 2026-02-14

### Added

- **`parse_notebook(content, source_path?)`** — Parse Jupyter notebook (.ipynb) JSON to
  (markdown_content, metadata) in the same shape as Markdown with frontmatter. Zero
  dependencies (stdlib `json` only). Supports nbformat 4.x. Converts cells to Markdown
  (fenced code blocks, output rendering). Extracts metadata (title, kernelspec, Jupytext).
  Exported from `patitas.notebook` and `patitas` top-level.

### Changed

- **MathRole** — Output raw LaTeX (no `\( \)` delimiters) to match plugin format for
  KaTeX `katex.render()` compatibility. Both plugin and role now emit identical structure.

## [0.2.0] - 2026-02-13

### Added

- **Incremental re-parsing** — `parse_incremental(new_source, previous, edit_start,
  edit_end, new_length)` accepts a previous AST and an edit range, identifies which
  top-level blocks overlap the edit, re-parses only that region, and splices new blocks
  back into the existing AST. Unaffected blocks are reused with adjusted offsets. Cost
  is O(change) rather than O(document). Falls back to full re-parse on failure.
  Exported from `patitas.incremental` and `patitas` top-level.

- **AST differ** — `diff_documents(old, new)` returns a tuple of `ASTChange` objects
  describing structural differences between two Document trees. Supports incremental
  builds, change detection, and live preview. Frozen-node equality makes identical
  subtrees O(1). Exported from `patitas.differ` and `patitas` top-level.

- **BaseVisitor and transform()** — `BaseVisitor` for typed AST traversal with
  `visit_*` dispatch; `transform(doc, fn)` for immutable bottom-up rewriting.
  Enables heading extraction, link collection, and structural rewrites without
  mutating the tree. Exported from `patitas.visitor` and `patitas` top-level.

- **Serialization** — `to_dict`, `from_dict`, `to_json`, `from_json` for JSON
  round-trip of AST nodes. Deterministic output for cache-key stability. Useful
  for caching parsed ASTs (Bengal incremental builds) and sending diffs over the
  wire (Purr SSE). Exported from `patitas.serialization` and `patitas` top-level.

- **Profiling** — `profiled_parse()`, `ParseAccumulator`, `get_parse_accumulator()`
  for parse-time profiling and bottleneck analysis.

- **ParserHost protocol** — Protocol for mixin contracts in the parser, enabling
  cleaner extension points.

### Fixed

- **`get_headings` thread-safety** — Rendering now uses `ContextVar` for
  heading context, fixing race conditions under free-threading.

### Changed

- CI type checker switched from mypy to ty.
- Coverage configuration with fail-under threshold.
- Removed dead `_peek` and `_advance` lexer methods.
- Removed unnecessary `from __future__ import annotations` imports.

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

[Unreleased]: https://github.com/lbliii/patitas/compare/v0.3.2...HEAD
[0.3.2]: https://github.com/lbliii/patitas/compare/v0.3.1...v0.3.2
[0.3.1]: https://github.com/lbliii/patitas/compare/v0.3.0...v0.3.1
[0.3.0]: https://github.com/lbliii/patitas/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/lbliii/patitas/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/lbliii/patitas/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lbliii/patitas/releases/tag/v0.1.0
