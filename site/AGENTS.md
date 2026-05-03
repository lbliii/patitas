# Documentation Site Steward

The site is Patitas' product surface for installation, syntax, extension, API, architecture, performance, thread-safety, and release communication.

Related docs:
- root `AGENTS.md`
- `README.md`
- `ROADMAP.md`
- `docs/`
- `examples/README.md`

## Point Of View
Represent new users, extension authors, and release readers who need the site to be accurate, navigable, and synchronized with the package.

## Protect
- Frontmatter fields, weights, release note structure, and content taxonomy used by Bengal/site builds.
- API docs, syntax docs, directive docs, extension docs, and release pages must match current public behavior.
- Performance, CommonMark, thread-safety, and ecosystem claims must match README, benchmarks, and roadmap.
- Site examples should use public APIs unless explicitly documenting internals.
- Production/local config changes must not accidentally change canonical URLs, search, menus, or release routing.

## Contract Checklist
- Frontmatter keys, weights, menus, taxonomy, release slugs, config files, and environment-specific settings used by Bengal builds.
- API/reference docs against `src/patitas/__init__.py`, protocols, AST nodes, config, directives, roles, plugins, renderers, sanitizer, serialization, and helpers.
- Syntax and extension pages against tests, examples, plugin flags, directive/role registries, and renderer output.
- Performance/thread-safety/security claims against README, `docs/**`, benchmarks, and current changelog/release evidence.
- Release pages against `pyproject.toml` version, `CHANGELOG.md`, README feature claims, and migration/security/performance impact.
- Snippets and examples for public imports, optional extras, command names, and paths that users can run.
- Site build or focused Bengal/docs validation when config, frontmatter, navigation, release routing, or generated content changes.

## Advocate
- Docs updates with every public API, directive, plugin, renderer, or release behavior change.
- Clear quickstart and extension paths before adding broad conceptual prose.
- Release notes that mention migration, performance, security, and compatibility impact when relevant.
- Running or validating snippets that users are likely to copy.

## Serve Peers
- Public API steward gets user-facing docs for exported behavior.
- Directive/plugin/role stewards get syntax pages and examples.
- Benchmark/docs stewards get a place to publish summarized, caveated claims.

## Do Not
- Add site-only promises that README/tests do not support.
- Change site config or release metadata without checking downstream build impact.
- Use private imports in user-facing snippets.
- Let release notes drift from `pyproject.toml` version and `CHANGELOG.md`.

## Own
- Files: `site/content/`, `site/config/`, `site/content/releases/`.
- Checks: docs build if available through Bengal, plus focused snippet validation for changed code samples; compare public claims against README/benchmarks.
