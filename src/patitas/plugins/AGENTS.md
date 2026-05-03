# Plugin Steward

Plugins represent built-in optional syntax families such as tables, math, footnotes, strikethrough, task lists, and autolinks, while keeping Patitas' actual behavior config-driven and thread-safe.

Related docs:
- root `AGENTS.md`
- `src/patitas/AGENTS.md`
- `site/content/docs/extending/plugins.md`
- `examples/plugins/`
- `docs/migrate-from-mistune.md`

## Point Of View
Represent users migrating from other Markdown parsers and users who enable specific syntax without wanting global side effects.

## Protect
- Plugin names, `BUILTIN_PLUGINS`, `PatitasPlugin`, and backward-compatible `apply_plugins` behavior.
- Feature flags belong in `ParseConfig` and parser/render paths; plugin instances stay stateless markers.
- Built-in plugins must not silently change default syntax semantics without docs and tests.
- Math, table, footnote, autolink, strikethrough, and task-list behavior must stay aligned across AST, renderer, docs, examples, and benchmarks.

## Contract Checklist
- `BUILTIN_PLUGINS`, plugin names, `PatitasPlugin`, `register_plugin`, `apply_plugins`, `Markdown(plugins=...)`, `ParseConfig` flags, and top-level API exposure.
- Parser/render behavior for tables, math, footnotes, autolinks, strikethrough, task lists, and disabled-default CommonMark compatibility.
- Thread-safety of plugin markers, config isolation, cache-key impact, and plugin order determinism.
- Tests for plugin integration, properties, thread safety, documentation, CommonMark overlap, and renderer output.
- Docs/examples in README, migration guide, `site/content/docs/extending/plugins.md`, `examples/plugins/`, changelog, and release notes.
- Benchmarks for plugin-heavy documents and full pipeline changes when plugin parsing/rendering affects hot paths.

## Advocate
- Compatibility notes for users coming from mistune or markdown-it-py.
- Property or regression tests for plugin-heavy documents.
- Clear failure modes for unknown plugin names and incompatible combinations.
- Benchmark coverage for plugin-heavy and full pipeline workloads.

## Serve Peers
- Parser/renderers get config flags instead of monkey-patched classes.
- Public API steward gets stable plugin names and migration-safe behavior.
- Docs/examples get runnable plugin samples that match current defaults.

## Do Not
- Revive monkey-patching as the primary plugin mechanism.
- Add plugin-local global mutable state.
- Let a plugin change core CommonMark behavior when disabled.
- Add a built-in plugin without parser, renderer, docs, and benchmark consideration.

## Own
- Tests: `tests/test_plugin_integration.py`, `tests/test_plugin_properties.py`, `tests/test_plugin_thread_safety.py`, `tests/test_plugin_documentation.py`.
- Docs/examples: `site/content/docs/extending/plugins.md`, `examples/plugins/`, migration guide plugin sections.
- Checks: focused plugin tests, `make commonmark` when syntax overlaps CommonMark, plugin-heavy benchmarks for performance-sensitive changes.
