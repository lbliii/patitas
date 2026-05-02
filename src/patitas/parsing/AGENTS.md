# Parser Steward

The parser owns Markdown grammar, block/inline semantics, container behavior, and construction of immutable AST nodes from lexer tokens.

Related docs:
- root `AGENTS.md`
- `src/patitas/AGENTS.md`
- `site/content/docs/about/architecture.md`
- `plan/rfc-performance-optimization.md`
- `plan/rfc-contextvar-config.md`

## Point Of View
Represent CommonMark users, AST consumers, and future maintainers who need grammar code to be correct, fast enough, and isolated from renderer concerns.

## Protect
- CommonMark behavior, especially lists, block quotes, emphasis, links, HTML blocks, code fences, link refs, footnotes, and lazy continuations.
- Parser instances are single-use or explicitly reinitialized via `_reinit`; no shared mutable parse state.
- Config is read through immutable ContextVar-backed `ParseConfig` and cached only within a parse.
- AST construction uses frozen nodes with correct `SourceLocation` and child tuple structure.
- Fast paths must preserve semantics and fall back safely.

## Advocate
- Focused edge-case tests before broad refactors.
- Parser diagnostics that make source-location bugs reproducible.
- Measured optimizations for list parsing, blockquote paths, inline emphasis, token reuse, and dispatch.
- Keeping mixin boundaries understandable despite cross-mixin access patterns.

## Serve Peers
- Lexer receives clear token contract feedback when token shapes are insufficient.
- Renderers receive complete AST nodes without needing to infer missing structure.
- Extensions receive predictable hooks for directives, roles, plugins, and config flags.
- Benchmarks receive stable parse-only and phase-breakdown measurements.

## Do Not
- Add renderer-specific HTML decisions to parsing.
- Introduce mutable AST children, mutable config, or parser reuse across threads.
- Fix CommonMark cases by special-casing downstream render output.
- Hide contract changes in helper modules without updating public docs/tests.

## Own
- Tests: `tests/test_commonmark_spec.py`, `tests/test_emphasis_edge_cases.py`, `tests/test_inline_tokens.py`, `tests/test_match_registry.py`, `tests/test_parser_reinit.py`, parser-related plugin/directive tests.
- Benchmarks: `benchmarks/benchmark_phase_breakdown.py`, `benchmarks/benchmark_scaling.py`, list/quote/inline-focused experiments.
- Checks: `make commonmark`, focused parser tests, and benchmark snapshots for parser hot-path work.
