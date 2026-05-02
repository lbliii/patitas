# Patitas Agent Constitution

## North Star
Patitas exists to prove that a pure-Python Markdown parser can be CommonMark-compliant, ReDoS-safe, typed, immutable, extension-friendly, and ready for Python 3.14 free-threading without coupling itself to Bengal, Purr, Kida, or any other orchestrator.

## Non-Negotiables
- Preserve CommonMark 0.31.2 compliance and the security promise of O(n), no-backtracking parsing.
- Keep AST nodes frozen, slotted, typed, and safe to share across threads.
- Keep parser and renderer state per-call or ContextVar-scoped; do not introduce shared mutable runtime state.
- Keep runtime dependencies minimal and explicit; optional features stay optional.
- Keep README, docs, site, examples, benchmarks, and release notes aligned with actual behavior.
- Do not add direct imports from Bengal, Purr, Kida, Rosettes orchestration, or downstream consumers into core Patitas.

## Architecture Boundaries
- `src/patitas/__init__.py` is the public API gate; exported names are downstream contracts.
- `nodes.py`, `tokens.py`, and `location.py` define AST/token/source-location contracts used by parsers, renderers, differs, serializers, and consumers.
- `lexer/` tokenizes in guaranteed forward progress; `parser.py` and `parsing/` build immutable AST from tokens.
- `directives/`, `plugins/`, and `roles/` are extension contracts; handlers must be stateless and registry/config driven.
- `renderers/`, `sanitize.py`, `text.py`, and `serialization.py` consume ASTs and must not weaken escaping, URL handling, LLM-safety, or deterministic output.
- `benchmarks/`, `docs/`, `site/`, `examples/`, and `plan/` own published claims, evidence, and future work.

## Stakes
Regressions can expose web apps to CPU denial-of-service, break Bengal/Purr incremental rendering, invalidate typed AST integrations, make threaded parsing unsafe, mislead users through stale performance/security claims, or leave extension authors with incompatible directive/plugin/role behavior.

## Stop And Ask
- Public API, exported type, AST shape, token, location, serialization, or renderer protocol changes.
- New runtime dependencies, optional extras, build/release pipeline changes, or Python version support changes.
- Config surface, plugin flag, directive/role registry, cache key, or ContextVar behavior changes.
- Security/auth/sanitization/HTML escaping/URL handling changes.
- Performance-sensitive, concurrency-sensitive, or hard-to-reverse parser/lexer changes.
- Data model migrations, irreversible release-note/history edits, or benchmark threshold changes.
- Test expectations and code behavior disagree, or a reported bug cannot be reproduced.

## Anti-Patterns
- Adding regex-based parsing or backtracking in lexer hot paths for a quick syntax win.
- Making AST nodes, tokens, configs, directive handlers, plugins, or role handlers mutable to simplify implementation.
- Fixing renderer output by post-processing HTML with regex instead of rendering correctly from the AST.
- Caching parse results without including config-sensitive behavior, or sharing `DictParseCache` across threads as if it were locked.
- Importing ecosystem projects into Patitas instead of exposing protocols and public exports.
- Updating README/site performance claims without benchmark evidence.

## Steward System
- Read this root file plus the closest scoped `AGENTS.md` before editing.
- Root is the constitution; scoped files are domain stewards.
- Scoped files own local invariants, refusal patterns, docs, tests, examples, fixtures, and checks.
- Cross-boundary work needs `Steward Notes` in PR descriptions naming consulted stewards, risks, checks, and unresolved tradeoffs.

Steward operating model:
- Point of View: who or what the domain represents.
- Protect: invariants, contracts, quality bars, and failure modes.
- Advocate: features, fixes, and investments the domain should push for.
- Serve Peers: upstream/downstream domains that need clearer contracts, diagnostics, docs, tests, or ergonomics.
- Do Not: local anti-patterns.
- Own: tests, docs, examples, fixtures, and maintenance checks.

## When To Consult
- Proactively consult stewards for cross-boundary, public-facing, hard-to-reverse, performance-sensitive, concurrency-sensitive, security-sensitive, or contract-affecting work.
- Use the nearest steward for local work.
- Use multiple stewards when ownership lines cross.
- Parallelize steward consultation only when questions are independent.
- Keep final synthesis with the implementing agent.

## Ask Stewards
Trigger phrase: `ask stewards`.

For implementation work, consult affected stewards. For backlog, roadmap, or prioritization work, consult all scoped stewards and produce a rollup with raw steward signals, confidence, dependencies, risks, convergence, minority reports, ranked backlog, and not-now items.

## Extension Routing
- Public API exports: `src/patitas/__init__.py`.
- AST/data contracts: `src/patitas/nodes.py`, `src/patitas/tokens.py`, `src/patitas/location.py`.
- Block directives: `src/patitas/directives/` plus directive parsing/rendering tests and docs.
- Inline roles: `src/patitas/roles/`.
- Built-in syntax plugins: `src/patitas/plugins/`, `src/patitas/config.py`, `src/patitas/parsing/`, and renderer support.
- Renderers: `src/patitas/renderers/`; optional syntax highlighting remains behind extras.

## Done Criteria
- Run focused tests for touched code; use `make test`, `make commonmark`, `make lint`, and `make ty` when scope warrants.
- Update docs/site/examples/changelog/release notes when public behavior, claims, or migration guidance changes.
- For performance work, include benchmark command and result context; for concurrency work, include threaded or ContextVar-specific checks.
- For security/sanitization work, include adversarial cases and note escaping/URL/HTML impact.
- For extension changes, include contract tests and at least one user-facing example or doc update.

## Review Notes
Flag surprises in PRs: public API drift, benchmark claim drift, CommonMark deltas, new dependency surface, thread-safety assumptions, cache-key assumptions, docs/examples that do not run, and any direct ecosystem coupling. Commit messages should name the domain first when practical, such as `lexer: preserve html block progress` or `docs: align benchmark claim`.
