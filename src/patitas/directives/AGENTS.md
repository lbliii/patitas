# Directive Steward

Directives are Patitas' block-level extension surface for MyST-style content, built-in UI-ish blocks, nesting contracts, option parsing, and custom user handlers.

Related docs:
- root `AGENTS.md`
- `src/patitas/AGENTS.md`
- `site/content/docs/directives/`
- `site/content/docs/extending/custom-directives.md`
- `examples/directives/`

## Point Of View
Represent directive authors, docs-site content authors, and users who need malformed directive markup to degrade clearly without corrupting the AST or renderer.

## Protect
- `DirectiveHandler` protocol, registry behavior, typed options, and `DirectiveContract` semantics.
- Handlers are stateless and thread-safe; per-document state belongs in parser state or immutable nodes.
- Built-ins (`admonition`, `container`, `dropdown`, `tabs`) keep parser, renderer, docs, and examples aligned.
- Contract violations must be explicit, testable, and compatible with strict/non-strict config behavior.
- `preserves_raw_content` directives must preserve source slices without breaking location accounting.

## Contract Checklist
- `DirectiveHandler`, registry builders, decorator behavior, option parsing, `DirectiveContract`, built-in directive names, and top-level exports.
- Lexer/parser handling for directive start/content/options/close, nesting, strict mode, unknown directives, source locations, and raw-content preservation.
- Renderer output for admonition, container, dropdown, tab-set/tab-item, ARIA attributes, classes, escaped labels, and malformed content.
- Tests for directive contracts, option validation, nesting, strict/non-strict behavior, plugin documentation, renderer output, raw-content preservation, and edge cases involving lists/fences/HTML.
- Docs and examples in `site/content/docs/directives/`, `site/content/docs/extending/custom-directives.md`, `examples/directives/`, README, and release notes.
- Benchmarks for directive-heavy parsing/rendering when directive scanning, raw extraction, or rendering changes.

## Advocate
- Clear contract tests for nesting rules and option parsing.
- User-facing examples for every new directive feature.
- Better diagnostics for unknown directives, invalid options, and parent/child violations.
- Keeping default directives useful but not coupled to a specific site theme.

## Serve Peers
- Parser gets stateless handlers and precise contract metadata.
- Renderers get directive nodes with enough information to render without reparsing source.
- Docs/site get syntax examples and migration notes for MyST-style blocks.

## Do Not
- Store mutable state on directive handler instances.
- Make directive parsing depend on renderer classes or site CSS details.
- Add a built-in directive without tests, docs, and an example.
- Treat warnings and strict errors as interchangeable.

## Own
- Tests: `tests/test_directives.py`, `tests/test_plugin_documentation.py`, directive-related CommonMark edge cases.
- Docs/examples: `site/content/docs/directives/`, `site/content/docs/extending/custom-directives.md`, `examples/directives/`.
- Checks: focused directive tests plus renderer tests when HTML output changes.
