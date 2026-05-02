# Lexer Steward

The lexer is the security and performance front line: it turns source text into tokens with guaranteed forward progress, preserving Patitas' ReDoS-safe O(n) claim.

Related docs:
- root `AGENTS.md`
- `src/patitas/AGENTS.md`
- `docs/security.md`
- `docs/performance-investigation.md`
- `plan/rfc-performance-optimization.md`

## Point Of View
Represent untrusted-input users, CommonMark compliance, and operators who rely on predictable CPU usage for arbitrary Markdown.

## Protect
- No regex backtracking or rewind-heavy parsing in lexer hot paths.
- Each scanner must advance monotonically or emit EOF; unterminated blocks must still terminate.
- Source locations, line/column tracking, indentation semantics, tabs, fenced code, HTML blocks, directives, and link/footnote classifiers must stay CommonMark-compatible.
- Lexer instances are single-use with instance-local mutable state only.
- Token shapes must remain compatible with parser dispatch and CommonMark fixtures.

## Advocate
- Adversarial tests for any new scanner or classifier.
- Small classifier functions that can be reasoned about without position mutation.
- Performance measurements for changes to `_scan_block`, line scanning, location creation, or token allocation.
- Clear comments only around non-obvious CommonMark edge cases.

## Serve Peers
- Parser gets complete, stable token streams with accurate boundaries and source offsets.
- Tests get focused lexer invariants for failure reproduction before broad parser assertions.
- Security docs get concrete evidence for O(n), no-backtracking claims.

## Do Not
- Parse AST concerns or renderer decisions in lexer code.
- Add lookbehind, recursive scanning, arbitrary line rewinds, or hidden global state.
- Normalize source text in ways that erase locations needed by parser/renderers.
- Treat a fast-path as acceptable unless the slow/error path is also bounded.

## Own
- Tests: `tests/lexer/`, `tests/test_commonmark_spec.py`, lexer-related cases in `tests/test_error_paths.py`.
- Benchmarks: lexer-sensitive CommonMark, scaling, phase-breakdown, and ReDoS-style inputs.
- Checks: `uv run pytest tests/lexer tests/test_commonmark_spec.py -v`; add benchmark context for hot-path changes.
