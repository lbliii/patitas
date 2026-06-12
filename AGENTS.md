# Patitas Agent Constitution

## North Star
Patitas exists to prove that a pure-Python Markdown parser can be CommonMark-compliant, ReDoS-safe, typed, immutable, extension-friendly, and ready for Python 3.14 free-threading without coupling itself to Bengal, Purr, Kida, or any other orchestrator.

## Non-Negotiables
- Preserve CommonMark 0.31.2 compliance and the security promise of no catastrophic backtracking (linear time for typical input; a few non-lexer paths remain super-linear on adversarial input — see docs/security.md#known-limitations).
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
- Root is the constitution, routing guide, and swarm protocol; scoped files are domain stewards.
- Scoped files own local invariants, refusal patterns, docs, tests, examples, fixtures, and checks.
- Cross-boundary work needs `Steward Notes` in PR descriptions naming consulted stewards, risks, checks, and unresolved tradeoffs.

Steward operating model:
- Point of View: who or what the domain represents.
- Protect: invariants, contracts, quality bars, and failure modes.
- Contract Checklist: concrete surfaces to inspect when this domain changes.
- Advocate: features, fixes, and investments the domain should push for.
- Serve Peers: upstream/downstream domains that need clearer contracts, diagnostics, docs, tests, or ergonomics.
- Do Not: local anti-patterns.
- Own: tests, docs, examples, fixtures, and maintenance checks.

## Contract Checklist
- Identify every surface that should agree: CLI/API, programmatic use, protocol, schema/types, UI, docs, examples, scaffold/templates, tests, benchmarks, changelog.
- Every accepted finding must name required proof and collateral updates, or explicitly say `no collateral: <reason>`.
- Docs, examples, and scaffold/templates move in the same PR as user-facing behavior unless synthesis records why they are unaffected.
- Contract-affecting PRs include a parity matrix when behavior spans multiple entrypoints.

## Steward Signal Format
Steward findings should be contract-oriented, evidence-backed, and collateral-aware.

Use this format:
- Steward:
- Area:
- Severity: P0/P1/P2/P3
- Invariant:
- Evidence:
- User Impact:
- Required Fix:
- Required Proof:
- Collateral:
- Confidence:

## Steward Swarms
When the user asks for `ask stewards`, `bugbash`, `review swarm`, or `steward synthesis`, and delegation is available:
- Spawn independent steward agents for affected domains.
- Each steward reads root plus its closest scoped `AGENTS.md`.
- Each steward advocates only for that domain's interests.
- Each steward returns findings in the Steward Signal Format.
- The implementing agent owns synthesis and final decisions.
- Stewards advise and create useful tension; they do not own the integrated implementation.
- Keep PR scope bounded to accepted findings and their proof/collateral.
- Defer unrelated steward suggestions to not-now/follow-up.

For backlog, roadmap, or prioritization work:
- Consult all scoped stewards.
- Produce raw steward signals, confidence, dependencies, risks, convergence, minority reports, ranked backlog, and not-now items.

## Steward Feedback Loop
- Steward miss: when a bug escapes an applicable steward, update the checklist, a regression test, a docs/snippet check, a routing rule, or record why the miss should not become policy.
- Steward overreach: when a steward repeatedly pulls unrelated work into PRs, narrow the checklist, split the steward, or move the concern to follow-up.
- Repeated high-quality findings should become checklist items.
- Repeated noisy findings should be pruned or clarified.
- Steward guidance evolves from evidence: escaped bugs, late collateral updates, CI/review misses, and recurring review comments.

## When To Consult
- Proactively consult stewards for cross-boundary, public-facing, hard-to-reverse, performance-sensitive, concurrency-sensitive, security-sensitive, or contract-affecting work.
- Use the nearest steward for local work.
- Use multiple stewards when ownership lines cross.
- Parallelize steward consultation only when questions are independent.
- Keep final synthesis and implementation accountability with the implementing agent.

## Ask Stewards
Trigger phrase: `ask stewards`.

For implementation work:
- Consult affected stewards.
- Return synthesis before or during the change.
- Include accepted/deferred findings, merged duplicates, minority reports, required proof, collateral updates, and not-now items.

For multi-surface work, include a parity matrix like:

| Contract | API/CLI | Programmatic | Protocol | Schema/Types | Docs | Examples | Tests |
|---|---|---|---|---|---|---|---|

For backlog, roadmap, or prioritization work, consult all scoped stewards and produce a rollup with raw steward signals, confidence, dependencies, risks, convergence, minority reports, ranked backlog, and not-now items.

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
- Every accepted steward finding has test/docs/example/benchmark proof or an explicit no-impact note.

## Review Notes
Flag surprises in PRs: public API drift, unused public names, suppressions, dead code, benchmark gaps, benchmark claim drift, CommonMark deltas, new dependency surface, free-threading assumptions, cache-key assumptions, docs/examples that do not run, steward disagreement, deferred/not-now findings, and any direct ecosystem coupling. Commit messages should name the domain first when practical, such as `lexer: preserve html block progress` or `docs: align benchmark claim`.
