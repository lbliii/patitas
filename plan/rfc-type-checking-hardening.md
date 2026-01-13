# RFC: Type Checking Hardening for Patitas

**Status:** Draft  
**Created:** 2026-01-12  
**Authors:** AI Assistant  

---

## Executive Summary

This RFC proposes a verified path to a clean `mypy --strict` run in Patitas. Code inspection confirms issues in mixin method signatures, generic `Directive` usage, directive handler variance, and plugin-set class attributes. Exact error counts must be refreshed with a new mypy run before execution.

**Goal:** Achieve a clean `mypy --strict` pass while maintaining current runtime behavior.

---

## Problem Statement

Prior runs reduced many errors, but the current baseline is stale. A fresh `mypy --strict` log is required; previous counts (151) should not be relied upon. Verified categories:

| Category | Status | Verified Root Cause (code) |
|----------|--------|----------------------------|
| Mixin method conflicts | Confirmed | `_try_classify_fence_start` signatures differ across `FenceClassifierMixin`, `QuoteClassifierMixin`, and `ListClassifierMixin` (`src/patitas/lexer/classifiers/{fence,quote,list}.py`) |
| Directive generics | Confirmed | `Directive` is generic (`src/patitas/nodes.py`), but parser and handlers return bare `Directive` (`src/patitas/parsing/blocks/directive.py`, `src/patitas/directives/builtins/admonition.py`) |
| Dynamic attributes | Confirmed | Plugins set class attrs like `_tables_enabled` without class declarations on lexer/parser (`src/patitas/plugins/table.py`, `src/patitas/parser.py`) |
| Protocol variance | Confirmed | `DirectiveHandler.parse` expects `DirectiveOptions`, but implementations use subclasses (e.g., `AdmonitionOptions`) causing incompatibility (`src/patitas/directives/protocol.py`, `src/patitas/directives/builtins/admonition.py`) |
| Miscellaneous | Needs data | Remaining issues require a new mypy run |

---

## Proposed Solutions

### 1. Mixin Method Conflicts

**Problem (verified):** `_try_classify_fence_start` signatures differ across mixins:
- `FenceClassifierMixin`: `(content, line_start, indent=0, *, change_mode=True)`
- `QuoteClassifierMixin`: `(content, line_start, indent, change_mode=True)`
- `ListClassifierMixin`: `(content, line_start, indent)`

**Plan:** Normalize to the most specific signature and update callers:

- Adopt `(content: str, line_start: int, indent: int = 0, *, change_mode: bool = True) -> Token | None`.
- Update all mixins to match and ensure call sites pass `change_mode` by keyword where required.
- Remove redundant stubs once signatures align; no `type: ignore[misc]` should be necessary after alignment.

### 2. Directive Generic Type Parameters

**Problem (verified):** `Directive` is generic (`src/patitas/nodes.py`), but parser and handlers return bare `Directive`, triggering missing-parameter errors (`src/patitas/parsing/blocks/directive.py`, `src/patitas/directives/builtins/admonition.py`).

**Plan:**

1. In handler implementations, return `Directive[ConcreteOptions]` (e.g., `Directive[AdmonitionOptions]`).
2. In parser fallback paths, return `Directive[DirectiveOptions]` or `Directive[Any]` when truly dynamic.
3. Add required imports (`Any`) where signatures become parameterized; avoid casts.

### 3. Runtime Dynamic Attributes

**Problem (verified):** Plugins set class attributes at runtime that are not declared on target classes, e.g., `_tables_enabled` in `TablePlugin.extend_lexer` (`src/patitas/plugins/table.py`) is not declared on `Lexer`/`Parser`.

**Plan:**

1. Declare `ClassVar[bool]` flags on affected classes (Lexer/Parser and any other plugin targets) with defaults of `False`.
2. Keep runtime semantics unchanged; this is additive typing metadata.

### 4. Protocol Variance Issues

**Problem (verified):** `DirectiveHandler.parse` in `src/patitas/directives/protocol.py` accepts `DirectiveOptions`, but concrete handlers use subclasses (e.g., `AdmonitionOptions`), causing incompatibility with the registry.

**Plan:**

- Introduce `TypeVar("TOptions", bound=DirectiveOptions, covariant=True)` on `DirectiveHandler`.
- Update `parse` return type to `Directive[TOptions]` and parameter `options: TOptions`.
- Adjust registry and builder types to `DirectiveHandler[Any]` to accept covariant handlers without narrowing.

### 5. Miscellaneous Type Fixes

Not enumerated—requires a fresh `mypy --strict` run to list remaining items. Handle case by case after the four verified categories are fixed.

---

## Implementation Plan

### Phase 1: Baseline and Quick Wins

1. Run `mypy --strict src/patitas` and capture the log.
2. Align `_try_classify_fence_start` signatures and call sites.
3. Add `ClassVar` plugin flags on lexer/parser (and any other plugin targets).
4. Add concrete generics to `Directive` returns in handlers and parser.
5. Make `DirectiveHandler` generic/covariant and adjust registry types.

### Phase 2: Refinement

1. Re-run mypy; fix any remaining directive/mixin fallout.
2. Add targeted protocol/self-type annotations if further mixin constraints appear.

### Phase 3: Hardening

1. Add type-focused tests for directives and lexer mixins (cover fence, quote, list).
2. Consider a configuration object for plugin flags if more flags accumulate.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Runtime behavior changes | Keep changes additive (signatures/types only) and run existing tests. |
| Performance impact from typing changes | Use `TYPE_CHECKING` guards where new protocols are introduced. |
| Increased code complexity | Keep patterns localized (shared signature alignment, simple `ClassVar` flags). |
| Stale baseline | Always refresh `mypy --strict` log before estimating scope. |

---

## Success Criteria

1. `mypy --strict src/patitas` passes with 0 errors (log captured).
2. All existing tests continue to pass.
3. No performance regression in benchmarks.
4. IDE autocomplete works correctly for public APIs.
