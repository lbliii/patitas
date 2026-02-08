# Roadmap

Strategic roadmap for Patitas, the content foundation of the Bengal Cat Family ecosystem.

Patitas isn't just a Markdown parser — it's the **typed content layer** that Bengal builds with, Purr diffs against, and the entire ecosystem shares. The roadmap reflects that dual role: hardening the ecosystem integration while building standalone value that no other Python parser offers.

---

## Current State (v0.1.1)

- CommonMark 0.31.2 compliance (652/652 spec examples)
- Hand-written FSM lexer — ReDoS-proof, O(n) guaranteed
- Typed AST with frozen dataclasses (`slots=True`)
- Free-threading safe (Python 3.14t)
- Zero runtime dependencies
- Plugins: tables, footnotes, math, strikethrough, task lists, autolinks
- Directives: admonitions, dropdowns, tabs, containers (MyST syntax)
- Roles: formatting, icons, math, references
- Parser pooling support (`Parser._reinit()`)
- ContextVar-based thread-local configuration

### Ecosystem consumers

| Project | How it uses Patitas |
|---|---|
| **Bengal** | Deep integration — lexer, parser, nodes, config, directives, roles, source locations |
| **Purr** | AST diffing for reactive content updates, structural comparison via `patitas.nodes` |

### The Patitas–Kida Bridge (via Purr)

Patitas and Kida have no direct dependency on each other. But they share deep architectural DNA (frozen dataclasses, visitor patterns, source location tracking, ContextVar thread-safety) and Purr already bridges their AST systems for reactive rendering:

```
Content edit
  → Patitas re-parse → AST diff (differ.py)
  → ReactiveMapper: AST node types → context paths (e.g., Heading → page.toc)
  → Kida block_metadata(): context paths → affected template blocks
  → Re-render only those blocks → Push via SSE
```

This collaboration is the core innovation in Purr. It works because:

1. **Patitas AST nodes are typed** — `type(node).__name__` gives reliable dispatch keys
2. **Patitas AST nodes are frozen** — `==` comparison enables O(1) unchanged-subtree skipping
3. **Kida block metadata is introspectable** — `template.block_metadata()` exposes per-block dependencies as `frozenset[str]`
4. **Both are thread-safe** — the entire chain runs under free-threading without locks

The roadmap deepens this relationship at every phase.

---

## Architecture: Protocols, Not Dependencies

The vertical integration strategy works **without coupling the libraries to each other**. Every optimization flows through protocols and extension points that are independently useful. No library imports another library. The orchestrators (Bengal, Purr) wire them together.

### The Principle

Each library exposes features that are useful standalone. Those features happen to compose when used together. The composition lives in the orchestration layer, not in the libraries themselves.

```
┌──────────────────────────────────────────────────────────┐
│              Bengal / Purr (orchestration)                │
│                                                          │
│  Registers patitas `is` tests in kida's environment      │
│  Registers rosettes `highlight` as a kida filter         │
│  Wires ParseAccumulator + RenderAccumulator together     │
│  Maps patitas AST diffs → kida block updates             │
│                                                          │
└──────┬──────────────────┬──────────────────┬─────────────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│   Patitas    │  │    Kida      │  │    Rosettes      │
│              │  │              │  │                   │
│ Frozen AST   │  │ block_meta() │  │ highlight(start,  │
│ Visitor      │  │ is_cacheable │  │   end)            │
│ Differ       │  │ purity       │  │ highlight_many()  │
│ Profiling    │  │ `is` tests   │  │ tokenize(start,   │
│ ContextVar   │  │ filters      │  │   end)            │
│              │  │ streaming    │  │                   │
│ Zero deps    │  │ Zero deps    │  │ Zero deps         │
│ Works alone  │  │ Works alone  │  │ Works alone       │
└──────────────┘  └──────────────┘  └──────────────────┘
```

### Why This Works

Each "cheat code" maps to a standalone feature in one library + an extension point in another, connected by the orchestrator:

| Optimization | Patitas provides | Kida/Rosettes provides | Orchestrator connects |
|---|---|---|---|
| **Block-level caching** | Frozen nodes (hashable `==`) | `is_cacheable()`, purity analysis | Cache keyed on AST subtree hash |
| **Surgical re-render** | AST differ, context mapping | `block_metadata()` dependencies | Diff → context paths → blocks |
| **Zero-copy highlight** | `source_start`/`source_end` on nodes | Rosettes `start`/`end` params | Pass indices directly, skip alloc |
| **AST-native templates** | Typed frozen nodes | Extensible `is` tests + filters | Register node `is` tests + render filters |
| **Content-aware streaming** | Typed node iteration | `render_stream()` generator | Template iterates AST, streams by priority |
| **Cross-layer profiling** | `ParseAccumulator` (ContextVar) | `RenderAccumulator` (ContextVar) | Combine both into unified report |
| **Free-threading** | ContextVar isolation | ContextVar isolation | All layers safe under 3.14t |

### What Someone Using Only One Library Gets

**Patitas alone** (without kida or Bengal):
- CommonMark parser with typed AST, ReDoS-proof, thread-safe
- Visitor protocol for AST walking
- Differ for content versioning
- Linting framework for content quality
- Works with Jinja, Django templates, or any other renderer

**Kida alone** (without patitas):
- Template engine with block metadata, purity analysis, streaming
- Works with any data model (dicts, dataclasses, ORM objects)
- Extensible `is` tests and filters for any domain
- Profiling and introspection built in

**Rosettes alone** (without patitas or kida):
- Syntax highlighter, 55 languages, Pygments-compatible CSS
- Works with any source code from any source
- `highlight_many()` for parallel batch processing

### What You Get When You Combine Them

The orchestrator unlocks optimizations that are **architecturally impossible** when any layer is a third-party black box — not because the libraries are coupled, but because they expose enough surface area for an orchestrator to reason across boundaries.

A Jinja-based stack can never achieve this because:
1. Jinja supports custom `is` tests, but its compiler has **no purity analysis** — it can't know whether a test is deterministic, so it can never skip re-evaluation
2. Jinja has **no block dependency metadata** — it can't tell you which blocks depend on which context paths, so surgical re-rendering is impossible
3. Jinja's `{{ content }}` is an opaque string — no structural access, no per-node caching
4. Pygments doesn't accept `start`/`end` for zero-copy tokenization
5. mistune returns `dict[str, Any]` — not hashable, not typed, not diffable

The constraint isn't that Jinja's extension points are too narrow — it's that Jinja **doesn't introspect its own templates** deeply enough for an orchestrator to reason across boundaries. Kida does.

The constraint isn't that their libraries are bad. It's that their **extension points don't expose enough information** for an orchestrator to optimize across boundaries. Yours do, by design.

---

## Foundation Library Sprint (v0.2.0) — COMPLETED

APIs that make Patitas and Rosettes "integration-ready" for the orchestration layer. All items are implemented, tested, and exported from `patitas.__init__`.

### Completed

- [x] **`BaseVisitor[T]`** — match-based dispatch to `visit_*` methods, automatic child walking (`patitas.visitor`)
- [x] **`transform(doc, fn)`** — immutable AST rewriting via `dataclasses.replace()` (`patitas.visitor`)
- [x] **`diff_documents(old, new)`** — structural diff on frozen ASTs, O(1) unchanged-subtree skip (`patitas.differ`)
- [x] **`context_paths_for(node)`** — maps AST node types to template context paths (`patitas.context`)
- [x] **`ParseAccumulator`** — opt-in ContextVar profiling for parse calls (`patitas.profiling`)
- [x] **`ASTRenderer` protocol** — stable renderer interface, `HtmlRenderer` conforms (`patitas.renderers.protocol`)
- [x] **JSON serialization** — `to_dict`, `from_dict`, `to_json`, `from_json` with deterministic output (`patitas.serialization`)
- [x] **Rosettes `HighlightAccumulator`** — opt-in ContextVar profiling for highlight calls (`rosettes.profiling`)

### What This Unblocked

After this sprint, the next epic is purely orchestration work in Bengal and Purr:

- **Bengal**: register patitas `is` tests in kida via `env.add_test()`, register rosettes `highlight` as kida filter, implement block-level caching keyed on frozen AST hash, wire `ParseAccumulator` + `RenderAccumulator` + `HighlightAccumulator` into unified profiling
- **Purr**: replace its own differ/mapper with `from patitas import diff_documents, context_paths_for`, use kida `is_cacheable()` + patitas AST equality to skip pure block re-renders, implement AST-keyed block caching

---

## Next Epic: Orchestration (Bengal + Purr)

No library-level work remaining — purely wiring the foundation libraries together.

### Bengal Orchestration

- [ ] Register patitas node `is` tests in kida environment (`env.add_test("heading", ...)`)
- [ ] Register rosettes `highlight` as kida filter (`env.add_filter("highlight", ...)`)
- [ ] Block-level caching keyed on frozen AST subtree hash
- [ ] Unified profiling: wire `ParseAccumulator` + `RenderAccumulator` + `HighlightAccumulator`
- [ ] Stable dependency contract (use only `patitas.__init__` public API)

### Purr Orchestration

- [ ] Replace `purr.content.differ` with `from patitas import diff_documents, ASTChange`
- [ ] Replace `purr.reactive.mapper.CONTENT_CONTEXT_MAP` with `from patitas import context_paths_for`
- [ ] AST-keyed block caching via kida `is_cacheable()` + patitas frozen equality
- [ ] Skip pure block re-renders when AST subtree unchanged
- [ ] End-to-end profiling across content-to-template boundary

---

## Future: Standalone Value (v0.3.0)

Make Patitas attractive outside the Bengal ecosystem.

### Additional Renderers

- [ ] `TerminalRenderer` — ANSI-colored Markdown for CLI tools
- [ ] `MarkdownRenderer` — round-trip (AST back to Markdown)

### Common Extensions

- [ ] **Definition lists** — `term\n: definition` syntax
- [ ] **Abbreviations** — `*[HTML]: Hyper Text Markup Language`
- [ ] **Attributes** — `{.class #id key=value}` on blocks and spans
- [ ] **Smart quotes and typography** — configurable, off by default

### Source Maps

Map rendered HTML positions back to source Markdown positions for in-browser editing, error reporting, and content validation.

### Public API Boundary

- [ ] Deprecation warnings for direct internal imports (`patitas.lexer`, `patitas.parser`, etc.)
- [ ] Document public vs internal API boundary

### GFM Spec Compliance

- [ ] Run GFM spec tests and report compliance numbers
- [ ] Align performance claims across README, pyproject.toml, docs

---

## Future: Platform Differentiator (v0.4.0+)

Things only Patitas can do because of its typed, immutable, thread-safe architecture.

### Content Linting Framework

A `ruff`-for-Markdown powered by the typed AST. Pattern matching on frozen dataclasses makes rule authoring trivial compared to regex-based linters.

```python
from patitas.lint import lint, LintRule

class NoSkippedHeadings(LintRule):
    id = "heading-increment"

    def check_heading(self, node: Heading, prev_level: int) -> Diagnostic | None:
        if node.level > prev_level + 1:
            return Diagnostic(node.location, f"Heading skips from h{prev_level} to h{node.level}")
```

### Incremental Parsing

Re-parse only changed blocks. When a user edits line 47 of a 500-line document, don't re-parse from scratch. This unlocks:

- Sub-millisecond re-parse in Purr's reactive pipeline
- Efficient large-document handling in Bengal
- Foundation for a language server

### AST-Native Template Expressions

Templates that operate on content structure directly:

```jinja
{% for node in page.ast.children %}
  {% if node is heading %}
    <h{{ node.level }} id="{{ node.id }}">{{ node | render_inline }}</h{{ node.level }}>
  {% elif node is fenced_code %}
    {{ node | highlight }}
  {% end %}
{% end %}
```

This is the deepest possible collaboration — eliminating the HTML-string bottleneck entirely via Kida `is` tests and filters that understand Patitas node types.

### Language Server Protocol

A Markdown LSP powered by Patitas:

- Autocomplete for directive names and role names
- Hover documentation for directives
- Diagnostics from the linting framework
- Go-to-definition for internal links
- Document symbols (heading outline)

---

## Explicitly Not Planned

| Item | Reason |
|---|---|
| **Beating mistune on raw single-thread speed** | Diminishing returns. The FSM architecture has a floor. The 6ms gap on the full CommonMark spec is imperceptible. Focus on where the architecture wins: safety, threading, typed AST. |
| **Python-Markdown compatibility layer** | Different spec, different API, different audience. Not worth the bridge. |
| **Python < 3.14 support** | The free-threading and modern syntax requirements are core to Patitas's identity. Backporting would compromise the design. If demand materializes, consider a `patitas-compat` package with `threading.Lock` fallbacks, but don't dilute the main package. |
| **Non-Markdown input formats** | Patitas parses Markdown. RST, AsciiDoc, and other formats are out of scope. |

---

## Ecosystem Integration Points

How each roadmap item connects back to the ecosystem:

| Roadmap Item | Bengal | Purr | Kida | Chirp | Pounce |
|---|---|---|---|---|---|
| ~~Visitor/Transformer~~ | AST transforms in render pipeline | Cleaner diff walks | Shared visitor pattern | — | — |
| ~~Context Mapping~~ | Content validation | Replaces hardcoded mapper | Block metadata consumer | — | — |
| ~~AST Differ~~ | — | Core reactive engine | Per-block cache invalidation | — | — |
| ~~Profiling APIs~~ | End-to-end page timing | Bottleneck identification | `RenderAccumulator` pairing | — | — |
| ~~ASTRenderer Protocol~~ | Stable renderer contract | — | — | — | — |
| ~~AST Serialization~~ | Disk caching for builds | AST diffs over SSE | — | — | Serve pre-parsed content |
| Orchestration wiring | `is` tests + filters + caching | AST-keyed block caching | Extension points consumed | — | — |
| Additional Renderers | Per-format output | — | — | MD fragments in responses | — |
| Source Maps | Validation with line numbers | Live preview editing | Error traces to source MD | — | — |
| Content Linting | `bengal lint` command | Real-time lint-on-save | — | — | — |
| AST-Native Templates | Eliminates HTML bottleneck | Per-block AST caching | `is` tests + filters for nodes | — | — |
| Incremental Parse | Faster incremental builds | Sub-ms reactive updates | — | — | — |
| Language Server | — | — | — | — | — (standalone) |

---

## Version Targets

| Version | Theme | Status |
|---|---|---|
| **0.2.0** | Foundation library sprint | **Done** — visitor, differ, context, profiling, renderer protocol, serialization |
| **0.3.0** | Standalone value | Planned — additional renderers, extensions, source maps |
| **0.4.0** | Platform differentiator | Planned — linting framework, incremental parsing, LSP |
| **1.0.0** | Stable API, full GFM, linting | When ready |

The 1.0.0 milestone means: public API is frozen, all internal imports are gated, GFM compliance is tracked, and the linting framework is usable. No rush — ship it when the contract is right.
