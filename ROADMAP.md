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

## Phase 1: Ecosystem Hardening (v0.2.0)

Make Patitas rock-solid for Bengal and Purr. Stabilize the API boundary. Formalize the Patitas–Kida collaboration points.

### AST Visitor & Transformer

Bengal, Purr, and Kida all walk ASTs manually today using similar patterns (`_visit_{nodetype}` dispatch). A proper `Visitor` protocol and `transform()` function in Patitas eliminates duplicated tree-walking code and opens the door to composable AST pipelines.

```python
from patitas import parse
from patitas.ast import Visitor, transform

class HeadingCollector(Visitor):
    def visit_heading(self, node: Heading) -> None:
        self.headings.append(node)

# Walk without modifying
collector = HeadingCollector()
collector.visit(doc)

# Transform (returns new immutable AST)
new_doc = transform(doc, shift_headings(by=1))
```

### Public API Boundary

Bengal currently imports internal modules directly (`patitas.lexer`, `patitas.parser`, `patitas.config`, `patitas.location`, `patitas.stringbuilder`). Define the contract:

- **Public** — everything in `patitas.__init__`, `patitas.nodes`, `patitas.config`
- **Stable** — `patitas.directives`, `patitas.roles`, `patitas.plugins`
- **Internal** — `patitas.lexer`, `patitas.parser`, `patitas.parsing`, `patitas.stringbuilder`

Ship a deprecation warning for direct internal imports. Give Bengal one release cycle to migrate.

### GFM Spec Compliance Tracking

Tables, strikethrough, task lists, and autolinks are already implemented as plugins. Run them against the [GFM spec](https://github.github.com/gfm/) and report compliance numbers. Many users think in terms of "GitHub Markdown" not "CommonMark."

### Performance Messaging Alignment

The pyproject.toml description claims "40-50% faster than mistune" but spec benchmarks show mistune winning (11ms vs 17ms). The honest framing is stronger: Patitas wins on large documents, wins massively on pathological input, and is the only safe option under free-threading. Align all messaging to that narrative.

### Content-Aware Context Mapping

Purr's `CONTENT_CONTEXT_MAP` (mapping `Heading → page.toc`, `FootnoteDef → page.footnotes`, etc.) is currently hardcoded in Purr. Move it into Patitas as a first-class API so any consumer can ask "what template context does this node type affect?"

```python
from patitas.context import context_paths_for

paths = context_paths_for(heading_node)
# frozenset({"page.toc", "page.headings", "page.body"})
```

This decouples the mapping from Purr and makes it reusable for Bengal's content validation, future Chirp Markdown rendering, or any tool that needs to understand the semantic impact of a content change.

### Milestone Checklist

- [ ] `Visitor` protocol with typed `visit_*` dispatch
- [ ] `transform()` returning new immutable AST
- [ ] Content-aware context mapping API (`patitas.context`)
- [ ] Document public vs internal API boundary
- [ ] Deprecation warnings for internal imports
- [ ] GFM spec test suite integration
- [ ] Align performance claims across README, pyproject.toml, docs

---

## Phase 2: Standalone Value (v0.3.0)

Make Patitas attractive outside the Bengal ecosystem. Add capabilities no other Python parser offers.

### Pluggable Renderers

An `ASTRenderer` protocol so consumers can render to anything — not just HTML.

```python
from typing import Protocol
from patitas.nodes import Document

class ASTRenderer(Protocol):
    def render(self, doc: Document) -> str: ...
```

Target renderers:
- `HtmlRenderer` — existing, becomes the reference implementation
- `TerminalRenderer` — ANSI-colored Markdown for CLI tools
- `MarkdownRenderer` — round-trip (AST back to Markdown)
- `JsonRenderer` — structured output for APIs and tooling

### AST Serialization

Enable AST caching between processes. Bengal could cache parsed ASTs to disk. Purr could send AST diffs over SSE. Pounce could serve pre-parsed content.

- JSON serialization/deserialization of the full AST
- Optional MessagePack for compact binary format
- Deterministic output for cache key stability

### Common Extensions

Extensions that are table stakes for documentation sites:

- **Definition lists** — `term\n: definition` syntax
- **Abbreviations** — `*[HTML]: Hyper Text Markup Language`
- **Attributes** — `{.class #id key=value}` on blocks and spans
- **Smart quotes and typography** — configurable, off by default

### Source Maps

Map rendered HTML positions back to source Markdown positions. The `SourceLocation` data already exists on every AST node — expose it in rendered output for:

- In-browser editing with live preview
- Error reporting with source line numbers
- Bengal's content validation with precise locations

### Milestone Checklist

- [ ] `ASTRenderer` protocol defined
- [ ] `TerminalRenderer` for CLI output
- [ ] `MarkdownRenderer` for round-tripping
- [ ] `JsonRenderer` for API output
- [ ] AST JSON serialization/deserialization
- [ ] Definition lists plugin
- [ ] Attributes plugin (`{.class #id}`)
- [ ] Source map emission in HTML renderer

---

## Phase 3: Platform Differentiator (v0.4.0+)

Things only Patitas can do because of its typed, immutable, thread-safe architecture.

### Content Linting Framework

A `ruff`-for-Markdown powered by the typed AST. Pattern matching on frozen dataclasses makes rule authoring trivial compared to regex-based linters.

Built-in rules:
- Heading hierarchy violations (h1 -> h3 skip)
- Broken internal links
- Duplicate heading IDs
- Accessibility checks (images without alt text)
- Style rules (line length, trailing whitespace)
- Custom rules via `LintRule` protocol

```python
from patitas.lint import lint, LintRule

class NoSkippedHeadings(LintRule):
    id = "heading-increment"

    def check_heading(self, node: Heading, prev_level: int) -> Diagnostic | None:
        if node.level > prev_level + 1:
            return Diagnostic(node.location, f"Heading skips from h{prev_level} to h{node.level}")
```

### AST Diffing API

Purr already does ad-hoc AST diffing. Promote it to a first-class API. Useful for CMSes, collaborative editing, content versioning, and Purr's reactive updates.

```python
from patitas.diff import diff, Change

changes: list[Change] = diff(old_doc, new_doc)
# [Change(kind="modified", path="/children/2", old=Paragraph(...), new=Paragraph(...))]
```

### Incremental Parsing

Re-parse only changed blocks. When a user edits line 47 of a 500-line document, don't re-parse from scratch. This unlocks:

- Sub-millisecond re-parse in Purr's reactive pipeline
- Efficient large-document handling in Bengal
- Foundation for a language server

### Cross-AST Profiling with Kida

Kida already has `RenderAccumulator` (opt-in profiling that tracks block timings, macro calls, filter usage). Patitas should expose a matching `ParseAccumulator` so the full content pipeline can be profiled end-to-end:

```python
from patitas.profiling import ParseAccumulator, profiled_parse

with profiled_parse() as stats:
    doc = parse(source)

stats.total_ms        # 2.1ms
stats.lexer_ms        # 0.8ms
stats.parser_ms       # 1.1ms
stats.fast_path_hits  # 47 of 93 blocks
stats.plugin_ms       # {"tables": 0.2ms}
```

Combined with Kida's `profiled_render()`, a framework like Bengal or Purr can answer: "This page took 50ms — 3ms parsing (patitas), 47ms rendering (kida), of which 30ms was the sidebar block." That's actionable profiling across the content-to-template boundary.

### AST-Native Template Expressions

Today, Bengal converts Patitas AST → HTML string → passes string to Kida template. The AST is discarded after rendering. In an AST-native model, Kida templates could directly access Patitas AST nodes:

```jinja
{# Instead of page.html_content (opaque string) #}
{% for node in page.ast.children %}
  {% if node is heading %}
    <h{{ node.level }} id="{{ node.id }}">{{ node | render_inline }}</h{{ node.level }}>
  {% elif node is fenced_code %}
    {{ node | highlight }}
  {% end %}
{% end %}
```

This requires:
- Kida `is` tests that understand Patitas node types
- Patitas filters registered in Kida's environment (`render_inline`, `highlight`)
- A shared protocol for "renderable AST node" that both libraries agree on

This is the deepest possible collaboration — templates that operate on content structure, not content strings. It would enable per-block caching (Kida caches the sidebar block because its AST inputs haven't changed), content-aware streaming (stream heading blocks first), and eliminates the HTML-string bottleneck entirely.

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
| Visitor/Transformer | AST transforms in render pipeline | Cleaner diff walks | Shared visitor pattern | — | — |
| Context Mapping API | Content validation | Replaces hardcoded mapper | Block metadata consumer | — | — |
| API Boundary | Stable dependency contract | Stable dependency contract | — | — | — |
| Pluggable Renderers | Per-format output | — | — | MD fragments in responses | — |
| AST Serialization | Disk caching for builds | AST diffs over SSE | — | — | Serve pre-parsed content |
| Source Maps | Validation with line numbers | Live preview editing | Error traces to source MD | — | — |
| Content Linting | `bengal lint` command | Real-time lint-on-save | — | — | — |
| AST Diffing | — | Core reactive engine | Per-block cache invalidation | — | — |
| Cross-AST Profiling | End-to-end page timing | Bottleneck identification | `RenderAccumulator` pairing | — | — |
| AST-Native Templates | Eliminates HTML bottleneck | Per-block AST caching | `is` tests + filters for nodes | — | — |
| Incremental Parse | Faster incremental builds | Sub-ms reactive updates | — | — | — |
| Language Server | — | — | — | — | — (standalone) |

---

## Version Targets

| Version | Theme | Target |
|---|---|---|
| **0.2.0** | Ecosystem hardening | Q1 2026 |
| **0.3.0** | Standalone value | Q2 2026 |
| **0.4.0** | Platform differentiator | Q3 2026 |
| **1.0.0** | Stable API, full GFM, linting | When ready |

The 1.0.0 milestone means: public API is frozen, all internal imports are gated, GFM compliance is tracked, and the linting framework is usable. No rush — ship it when the contract is right.
