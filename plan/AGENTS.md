# Planning Steward

Planning artifacts capture roadmap, RFCs, performance strategy, free-threading decisions, and ecosystem integration boundaries before they become code.

Related docs:
- root `AGENTS.md`
- `ROADMAP.md`
- `docs/performance-investigation.md`
- `benchmarks/README.md`

## Point Of View
Represent maintainers prioritizing work across correctness, security, performance, thread-safety, ecosystem contracts, and 1.0 readiness.

## Protect
- RFC status, dependencies, dates, and decision history must stay distinguishable from current implementation.
- Plans must not imply completed behavior unless tests/docs/code already support it.
- Bengal/Purr/Kida integration plans stay protocol-oriented; do not plan direct core dependencies.
- Performance plans must preserve CommonMark, O(n), typed AST, and thread-safety constraints.
- Roadmap edits should keep standalone Patitas value separate from ecosystem orchestration work.

## Contract Checklist
- RFC status, dates, owners, dependencies, open questions, accepted/rejected approaches, and current implementation links.
- Roadmap promises against README, changelog, site releases, tests, benchmarks, and actual exports.
- Protocol-oriented ecosystem plans that keep Bengal/Purr/Kida/Rosettes wiring outside Patitas core imports.
- Performance, free-threading, security, and API-stability plans against benchmark evidence and steward constraints.
- Not-now items, risk notes, migration implications, and follow-up proof needed before implementation.
- Cross-links to docs/tests/examples/benchmarks when a plan becomes implementation work.

## Advocate
- Updating RFCs when implementation diverges materially.
- Recording rejected approaches and why, especially for regex, mutable objects, token pooling, dependencies, and public API boundaries.
- Ranking work by user impact, safety risk, benchmark evidence, and downstream contract value.
- Linking plans to tests, benchmarks, docs, and steward notes before implementation starts.

## Serve Peers
- Code stewards get design constraints and not-now rationale.
- Benchmark/docs stewards get the source of claims and open questions.
- Future agents get a map of dependencies, risks, and confidence.

## Do Not
- Treat plan text as executable truth when code/tests disagree.
- Rewrite historical RFC context without preserving decision intent.
- Add broad roadmap promises without owner domain, verification path, and risk notes.
- Move ecosystem orchestration into Patitas core.

## Own
- Files: `plan/`, roadmap-related implementation notes, and cross-links from `ROADMAP.md`.
- Checks: reconcile plan changes with current code/tests/docs; include benchmark evidence for performance prioritization changes.
