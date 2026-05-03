# Renderer Steward

Renderers turn immutable ASTs into HTML or LLM-friendly text while preserving security defaults, deterministic output, and thread-safe per-render state.

Related docs:
- root `AGENTS.md`
- `src/patitas/AGENTS.md`
- `site/content/docs/about/architecture.md`
- `site/content/docs/extending/llm-safety.md`
- `docs/security.md`

## Point Of View
Represent application users who feed Patitas output into browsers, LLM context, docs sites, and downstream pipelines.

## Protect
- HTML escaping, URL encoding, heading slug generation, footnote collection, directive/role rendering, and optional highlighting behavior.
- Per-render mutable state stays in `RenderContext` or ContextVar-scoped storage, not shared renderer instance state.
- `ASTRenderer` remains a stable protocol for alternate renderers.
- `render_llm` and sanitization workflows must not reintroduce dangerous HTML, URLs, or zero-width content.
- Renderer changes must preserve deterministic output for tests, docs, and snapshots.

## Contract Checklist
- `HtmlRenderer`, `LlmRenderer`, `ASTRenderer`, `RenderContext`, `StringBuilder`, highlighter/icon resolver protocols, and top-level `render`/`render_llm` exports.
- Escaping and URL handling for text, inline HTML, HTML blocks, links, images, roles, directives, math, footnotes, code blocks, and heading IDs.
- Per-render state such as heading slug counters, footnote collection, directive registry use, source slices, and ContextVar-backed helpers.
- Sanitizer and LLM-safety interactions in `sanitize.py`, `text.py`, `renderers/llm.py`, README, docs, site, and examples.
- Tests for renderer output, edge cases, LLM output, sanitization, directives/plugins/roles, and deterministic serialization-sensitive rendering.
- Docs/examples/changelog when rendered HTML, LLM text, highlighting, escaping, URL behavior, or renderer protocols change.
- Benchmarks for render-heavy and full-pipeline workloads when output hot paths or `StringBuilder` behavior changes.

## Advocate
- Renderer tests for every AST node added or changed.
- Security-focused cases for HTML blocks, inline HTML, links, images, roles, directives, and LLM output.
- Clear public examples for custom renderer, highlighter, icon, directive, and role integration.
- Performance checks for string-building changes.

## Serve Peers
- Parser gets feedback when AST lacks enough structure to render safely.
- Directives/roles get renderer hooks without stateful handlers.
- Docs/examples get exact output expectations and migration notes.

## Do Not
- Post-process rendered HTML with regex to fix structural mistakes.
- Store footnotes, heading slugs, or other per-render state on renderer instances.
- Bypass `html_escape`/URL encoding for user-provided content.
- Add optional highlighter behavior as a required runtime dependency.

## Own
- Tests: `tests/test_renderer.py`, `tests/test_renderer_edge_cases.py`, `tests/test_renderer_llm.py`, `tests/test_sanitize.py`, renderer portions of directive/plugin/role tests.
- Docs/examples: LLM safety docs/examples, architecture renderer section, custom renderer guidance.
- Checks: focused renderer tests, security tests for escaping/sanitization changes, benchmark phase-breakdown for output hot paths.
