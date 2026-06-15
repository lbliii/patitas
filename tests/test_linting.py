"""Tests for the patitas.linting content-linting framework (issue #56).

Covers Diagnostic formatting/severity, the LintContext, the polymorphic
``lint()`` entrypoint (str + Document paths), runner stamping + sort
determinism, each of the three starter rules (positive/negative/edge cases),
the registry/builder, the LintRule protocol, property/idempotence invariants,
thread safety, and a dogfood pass over the repo's own docs.

Run focused:
    cd /Users/llane/conductor/workspaces/patitas/tokyo && uv run pytest tests/test_linting.py -q
"""

import dataclasses
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

import patitas
from patitas import lint, parse
from patitas.linting import (
    Diagnostic,
    HeadingIncrementRule,
    LintContext,
    Linter,
    LintRule,
    LintRuleRegistry,
    LintRuleRegistryBuilder,
    NoEmptyLinkRule,
    Severity,
    TrailingWhitespaceRule,
    create_default_lint_registry,
)
from patitas.location import SourceLocation
from patitas.nodes import Document, Heading, Image, Link, Paragraph, Text

LOC = SourceLocation(lineno=1, col_offset=1)


def _doc(*blocks):  # type: ignore[no-untyped-def]
    return Document(location=LOC, children=tuple(blocks))


def _heading(level: int, *inlines, loc: SourceLocation = LOC):  # type: ignore[no-untyped-def]
    return Heading(location=loc, level=level, children=tuple(inlines))  # type: ignore[arg-type]


def _para(*inlines):  # type: ignore[no-untyped-def]
    return Paragraph(location=LOC, children=tuple(inlines))


def _text(content: str) -> Text:
    return Text(location=LOC, content=content)


def _link(url: str, *children):  # type: ignore[no-untyped-def]
    return Link(location=LOC, url=url, title=None, children=tuple(children))


# =============================================================================
# Diagnostic + Severity
# =============================================================================


class TestDiagnostic:
    def test_str_with_source_file(self) -> None:
        loc = SourceLocation(lineno=10, col_offset=5, source_file="x.md")
        diag = Diagnostic(rule_id="my-rule", message="oops", location=loc)
        assert str(diag) == "x.md:10:5: [my-rule] oops"

    def test_str_without_source_file(self) -> None:
        loc = SourceLocation(lineno=10, col_offset=5)
        diag = Diagnostic(rule_id="my-rule", message="oops", location=loc)
        assert str(diag) == "10:5: [my-rule] oops"

    def test_to_dict_keys_and_severity_value(self) -> None:
        loc = SourceLocation(lineno=2, col_offset=3, source_file="f.md")
        diag = Diagnostic(rule_id="r", message="m", location=loc, severity=Severity.ERROR)
        d = diag.to_dict()
        assert d["rule_id"] == "r"
        assert d["message"] == "m"
        assert d["severity"] == "error"  # serializes to .value
        assert d["line"] == 2
        assert d["col"] == 3
        assert d["source_file"] == "f.md"

    def test_default_severity_is_warning(self) -> None:
        diag = Diagnostic(rule_id="r", message="m", location=LOC)
        assert diag.severity is Severity.WARNING

    def test_is_frozen(self) -> None:
        diag = Diagnostic(rule_id="r", message="m", location=LOC)
        with pytest.raises(dataclasses.FrozenInstanceError):
            diag.rule_id = "other"  # type: ignore[misc]

    def test_is_slotted(self) -> None:
        diag = Diagnostic(rule_id="r", message="m", location=LOC)
        assert not hasattr(diag, "__dict__")


class TestSeverity:
    def test_is_plain_enum_not_int(self) -> None:
        # Not an IntEnum: no accidental int coercion.
        assert Severity.ERROR != 1
        assert not isinstance(Severity.ERROR, int)

    def test_to_lsp_mapping(self) -> None:
        assert Severity.ERROR.to_lsp() == 1
        assert Severity.WARNING.to_lsp() == 2
        assert Severity.INFO.to_lsp() == 3

    def test_values(self) -> None:
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"
        assert Severity.INFO.value == "info"


# =============================================================================
# LintContext
# =============================================================================


class TestLintContext:
    def test_lines_splits_on_newline(self) -> None:
        src = "a\nb\nc"
        ctx = LintContext(document=_doc(), source=src)
        assert ctx.lines == ("a", "b", "c")

    def test_lines_does_not_oversplit_on_formfeed(self) -> None:
        # str.splitlines() would over-split on \x0c / \x0b; split('\n') must not.
        src = "line1\x0cstill1\nline2\x0bstill2"
        ctx = LintContext(document=_doc(), source=src)
        assert ctx.lines == ("line1\x0cstill1", "line2\x0bstill2")

    def test_nodes_of_type_document_order_including_nested(self) -> None:
        src = "# Top\n\n> ## Nested\n"
        doc = parse(src)
        ctx = LintContext(document=doc, source=src)
        headings = ctx.nodes_of_type(Heading)
        assert [h.level for h in headings] == [1, 2]

    def test_headings_equals_nodes_of_type_heading(self) -> None:
        src = "# A\n\n## B\n"
        doc = parse(src)
        ctx = LintContext(document=doc, source=src)
        assert ctx.headings() == ctx.nodes_of_type(Heading)

    def test_is_frozen_and_slotted(self) -> None:
        ctx = LintContext(document=_doc(), source="x")
        assert not hasattr(ctx, "__dict__")
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.source = "y"  # type: ignore[misc]

    def test_derived_state_computed_eagerly(self) -> None:
        # Accessing lines/nodes on a frozen instance must work (computed in __post_init__).
        ctx = LintContext(document=_doc(_para(_text("hi"))), source="hi")
        assert ctx.lines == ("hi",)
        assert len(ctx.nodes_of_type(Text)) == 1


# =============================================================================
# Entrypoint: str / Document / Document-without-text
# =============================================================================


class TestEntrypointStrPath:
    def test_str_runs_all_rules(self) -> None:
        diags = lint("# H1\n\n### H3   ")
        ids = {d.rule_id for d in diags}
        assert "heading-increment" in ids
        assert "trailing-whitespace" in ids


class TestEntrypointDocumentPath:
    def test_document_with_text_matches_str_path(self) -> None:
        src = "# H1\n\n### H3   "
        doc = parse(src, source_file="x.md")
        from_doc = lint(doc, text=src, source_file="x.md")
        from_str = lint(src, source_file="x.md")
        assert [(d.rule_id, str(d.location)) for d in from_doc] == [
            (d.rule_id, str(d.location)) for d in from_str
        ]


class TestEntrypointDocumentNoText:
    def test_document_without_text_runs_ast_rules_only(self) -> None:
        src = "# H1\n\n### H3   "
        doc = parse(src)
        diags = lint(doc)  # no text=
        ids = {d.rule_id for d in diags}
        assert "heading-increment" in ids  # AST rule still fires
        assert "trailing-whitespace" not in ids  # no source -> no trailing-ws


# =============================================================================
# Runner: stamping + sort determinism
# =============================================================================


@dataclasses.dataclass(frozen=True, slots=True)
class _MisbehavingRule:
    rule_id = "well-behaved-id"
    default_severity = Severity.ERROR

    def check(self, ctx: LintContext):  # type: ignore[no-untyped-def]
        # Deliberately emit the WRONG rule_id and severity.
        yield Diagnostic(
            rule_id="WRONG-ID",
            message="x",
            location=SourceLocation(lineno=1, col_offset=1),
            severity=Severity.INFO,
        )


class TestRunnerStamping:
    def test_runner_overwrites_rule_id_and_severity(self) -> None:
        diags = lint("# H1", rules=[_MisbehavingRule()])
        assert len(diags) == 1
        assert diags[0].rule_id == "well-behaved-id"  # stamped, not "WRONG-ID"
        assert diags[0].severity is Severity.ERROR  # stamped, not INFO


class TestRunnerSortingDeterminism:
    def test_sorted_and_deterministic(self) -> None:
        src = "# H1\n\n### H3   \n\nmore   "
        a = lint(src)
        b = lint(src)
        assert a == b  # determinism
        keys = [(d.location.offset, d.location.lineno, d.location.col_offset, d.rule_id) for d in a]
        assert keys == sorted(keys)  # sorted

    def test_empty_rules_returns_empty(self) -> None:
        assert lint("# H1\n\n### H3", rules=()) == []


# =============================================================================
# heading-increment
# =============================================================================


class TestHeadingIncrement:
    def _ids(self, doc: Document):  # type: ignore[no-untyped-def]
        return list(HeadingIncrementRule().check(LintContext(document=doc)))

    def test_h1_to_h3_flagged_at_h3_location(self) -> None:
        h3_loc = SourceLocation(lineno=3, col_offset=1)
        doc = _doc(_heading(1, _text("a")), _heading(3, _text("b"), loc=h3_loc))
        diags = self._ids(doc)
        assert len(diags) == 1
        assert diags[0].location is h3_loc

    def test_h1_h3_h5_yields_two(self) -> None:
        doc = _doc(_heading(1), _heading(3), _heading(5))
        assert len(self._ids(doc)) == 2

    def test_monotonic_no_flag(self) -> None:
        doc = _doc(_heading(1), _heading(2), _heading(3))
        assert self._ids(doc) == []

    def test_decrease_no_flag(self) -> None:
        doc = _doc(_heading(3), _heading(1))
        assert self._ids(doc) == []

    def test_equal_no_flag(self) -> None:
        doc = _doc(_heading(2), _heading(2))
        assert self._ids(doc) == []

    def test_first_heading_any_level_not_flagged(self) -> None:
        doc = _doc(_heading(3))
        assert self._ids(doc) == []

    def test_setext_heading_participates(self) -> None:
        src = "Setext\n======\n\n#### Deep\n"
        doc = parse(src)
        diags = HeadingIncrementRule().check(LintContext(document=doc, source=src))
        # setext h1 -> atx h4 is a skip
        assert len(list(diags)) == 1

    def test_nested_heading_included(self) -> None:
        src = "# Top\n\n> ### Nested\n"
        doc = parse(src)
        diags = list(HeadingIncrementRule().check(LintContext(document=doc, source=src)))
        assert len(diags) == 1  # h1 -> h3 across container boundary

    def test_empty_doc_zero(self) -> None:
        assert self._ids(_doc()) == []


# =============================================================================
# no-empty-link
# =============================================================================


class TestNoEmptyLink:
    def _check(self, doc: Document):  # type: ignore[no-untyped-def]
        return list(NoEmptyLinkRule().check(LintContext(document=doc)))

    def test_no_children_flagged(self) -> None:
        doc = _doc(_para(_link("http://x")))
        diags = self._check(doc)
        assert len(diags) == 1
        assert "http://x" in diags[0].message

    def test_whitespace_only_flagged(self) -> None:
        doc = _doc(_para(_link("http://x", _text("   "))))
        assert len(self._check(doc)) == 1

    def test_text_not_flagged(self) -> None:
        doc = _doc(_para(_link("http://x", _text("click"))))
        assert self._check(doc) == []

    def test_bold_not_flagged_via_parse(self) -> None:
        src = "[**bold**](http://x)"
        doc = parse(src)
        assert list(NoEmptyLinkRule().check(LintContext(document=doc, source=src))) == []

    def test_image_only_not_flagged(self) -> None:
        img = Image(location=LOC, url="img.png", alt="alt")
        doc = _doc(_para(_link("http://x", img)))
        assert self._check(doc) == []

    def test_codespan_not_flagged_via_parse(self) -> None:
        src = "[`x`](http://x)"
        doc = parse(src)
        assert list(NoEmptyLinkRule().check(LintContext(document=doc, source=src))) == []

    def test_image_node_itself_never_flagged(self) -> None:
        img = Image(location=LOC, url="img.png", alt="")
        doc = _doc(_para(img))
        assert self._check(doc) == []

    def test_multiple_empty_links_each_emit(self) -> None:
        doc = _doc(_para(_link("http://a"), _text(" "), _link("http://b")))
        diags = self._check(doc)
        assert len(diags) == 2
        assert {d.message.count("http://") for d in diags} == {1}


# =============================================================================
# trailing-whitespace
# =============================================================================


class TestTrailingWhitespace:
    def _check(self, src: str, doc: Document | None = None):  # type: ignore[no-untyped-def]
        document = doc if doc is not None else parse(src)
        return list(TrailingWhitespaceRule().check(LintContext(document=document, source=src)))

    def test_trailing_spaces_flagged_with_col_and_count(self) -> None:
        diags = self._check("a   ", doc=_doc(_para(_text("a"))))
        assert len(diags) == 1
        assert diags[0].location.col_offset == 2  # after 'a'
        assert "3 character" in diags[0].message

    def test_whitespace_only_line_col_one(self) -> None:
        diags = self._check("   ", doc=_doc())
        assert len(diags) == 1
        assert diags[0].location.col_offset == 1

    def test_clean_lines_zero(self) -> None:
        diags = self._check("clean line\nanother", doc=_doc(_para(_text("clean line"))))
        assert diags == []

    def test_crlf_no_real_trailing_ws_not_flagged(self) -> None:
        diags = self._check("a\r", doc=_doc(_para(_text("a"))))
        assert diags == []

    def test_hard_break_two_spaces_flagged_at_info(self) -> None:
        diags = self._check("a  \nb", doc=_doc(_para(_text("a"), _text("b"))))
        assert len(diags) == 1
        assert diags[0].severity is Severity.INFO

    def test_code_block_excluded_surrounding_flagged(self) -> None:
        # Multi-line fence (>2 content lines) with trailing whitespace BEYOND
        # the first content line. A [lineno, lineno+1]-based exclusion would
        # leak lines 5+; the source_end-derived span must cover the whole fence.
        src = (
            "text   \n"  # 1: paragraph, flagged
            "\n"  # 2
            "```\n"  # 3: opening fence
            "code1   \n"  # 4: content (first)
            "code2   \n"  # 5: content (beyond first)
            "code3   \n"  # 6: content
            "    \n"  # 7: whitespace-only content
            "```\n"  # 8: closing fence
        )
        diags = self._check(src)
        flagged_lines = {d.location.lineno for d in diags}
        # The paragraph line is flagged.
        assert 1 in flagged_lines
        # No line inside the fence (4-8 content/fence) is flagged.
        assert flagged_lines.isdisjoint({4, 5, 6, 7, 8})

    def test_multiline_fence_no_false_positive(self) -> None:
        # Regression: a 5-content-line fence whose non-first content lines
        # carry trailing whitespace must yield ZERO trailing-ws diagnostics.
        src = (
            "```python\n"  # 1
            "a = 1   \n"  # 2
            "b = 2   \n"  # 3
            "c = 3   \n"  # 4
            "d = 4   \n"  # 5
            "   \n"  # 6: whitespace-only inside the fence
            "```\n"  # 7
        )
        diags = self._check(src)
        assert diags == []

    def test_multiline_indented_code_no_false_positive(self) -> None:
        # Regression: a >=3-line indented block with trailing whitespace on its
        # last line must not be flagged (end_lineno-based exclusion leaked it).
        src = (
            "para\n"  # 1
            "\n"  # 2
            "    code1   \n"  # 3
            "    code2   \n"  # 4
            "    code3   \n"  # 5: last content line, trailing ws
        )
        diags = self._check(src)
        assert diags == []

    def test_no_final_newline_flagged(self) -> None:
        diags = self._check("x   ", doc=_doc(_para(_text("x"))))
        assert len(diags) == 1

    def test_empty_source_zero(self) -> None:
        diags = self._check("", doc=_doc())
        assert diags == []

    def test_lineno_matches_with_formfeed(self) -> None:
        # split('\n') keeps form-feed inside the line; lineno stays in sync.
        src = "a\x0cb   \nclean"
        diags = self._check(src, doc=_doc(_para(_text("a"))))
        assert len(diags) == 1
        assert diags[0].location.lineno == 1


# =============================================================================
# Registry + builder
# =============================================================================


class TestRegistry:
    def test_build_and_get(self) -> None:
        reg = LintRuleRegistryBuilder().register(HeadingIncrementRule()).build()
        assert reg.get("heading-increment") is not None
        assert "heading-increment" in reg
        assert len(reg) == 1

    def test_duplicate_id_raises_value_error(self) -> None:
        builder = LintRuleRegistryBuilder().register(HeadingIncrementRule())
        with pytest.raises(ValueError, match="already registered"):
            builder.register(HeadingIncrementRule())

    def test_missing_metadata_raises_type_error(self) -> None:
        class Bogus:
            pass

        with pytest.raises(TypeError):
            LintRuleRegistryBuilder().register(Bogus())  # type: ignore[arg-type]

    def test_rules_preserve_registration_order(self) -> None:
        reg = (
            LintRuleRegistryBuilder()
            .register(NoEmptyLinkRule())
            .register(HeadingIncrementRule())
            .build()
        )
        assert [r.rule_id for r in reg.rules] == ["no-empty-link", "heading-increment"]

    def test_register_all(self) -> None:
        reg = (
            LintRuleRegistryBuilder()
            .register_all([HeadingIncrementRule(), NoEmptyLinkRule()])
            .build()
        )
        assert len(reg) == 2

    def test_default_registry_has_three(self) -> None:
        reg = create_default_lint_registry()
        assert len(reg) == 3
        assert isinstance(reg, LintRuleRegistry)
        for rid in ("heading-increment", "no-empty-link", "trailing-whitespace"):
            assert rid in reg

    def test_registry_no_public_mutation(self) -> None:
        reg = create_default_lint_registry()
        assert not hasattr(reg, "register")


# =============================================================================
# Protocol
# =============================================================================


class TestLintRuleProtocol:
    def test_starter_rules_satisfy_protocol(self) -> None:
        assert isinstance(HeadingIncrementRule(), LintRule)
        assert isinstance(NoEmptyLinkRule(), LintRule)
        assert isinstance(TrailingWhitespaceRule(), LintRule)

    def test_starter_rule_metadata(self) -> None:
        assert HeadingIncrementRule.rule_id == "heading-increment"
        assert HeadingIncrementRule.default_severity is Severity.WARNING
        assert NoEmptyLinkRule.rule_id == "no-empty-link"
        assert NoEmptyLinkRule.default_severity is Severity.WARNING
        assert TrailingWhitespaceRule.rule_id == "trailing-whitespace"
        assert TrailingWhitespaceRule.default_severity is Severity.INFO

    def test_custom_rule_runs_via_rules_kwarg(self) -> None:
        @dataclasses.dataclass(frozen=True, slots=True)
        class NoExclamationRule:
            rule_id = "no-exclaim"
            default_severity = Severity.WARNING

            def check(self, ctx: LintContext):  # type: ignore[no-untyped-def]
                for i, line in enumerate(ctx.lines, start=1):
                    if "!" in line:
                        yield Diagnostic(
                            rule_id=self.rule_id,
                            message="exclamation",
                            location=SourceLocation(lineno=i, col_offset=1),
                        )

        diags = lint("hello!\nworld", rules=[NoExclamationRule()])
        assert len(diags) == 1
        assert diags[0].rule_id == "no-exclaim"


# =============================================================================
# Linter
# =============================================================================


class TestLinter:
    def test_default_linter_matches_lint(self) -> None:
        src = "# H1\n\n### H3   "
        assert Linter().lint(src) == lint(src)

    def test_custom_registry(self) -> None:
        reg = LintRuleRegistryBuilder().register(HeadingIncrementRule()).build()
        diags = Linter(reg).lint("# H1\n\n### H3   ")
        assert {d.rule_id for d in diags} == {"heading-increment"}


# =============================================================================
# Property: determinism + clean-input invariant
# =============================================================================

_markdownish = st.text(alphabet="abcXYZ 0123\n#*_`>-[]()!|~^:.", max_size=120)


class TestPropertyDeterminism:
    @given(source=_markdownish)
    @settings(max_examples=80, suppress_health_check=[HealthCheck.too_slow])
    def test_lint_is_deterministic(self, source: str) -> None:
        assert lint(source) == lint(source)

    @given(source=_markdownish)
    @settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
    def test_lint_never_raises_and_returns_list(self, source: str) -> None:
        out = lint(source)
        assert isinstance(out, list)


class TestPropertyCleanInput:
    @given(levels=st.lists(st.integers(min_value=1, max_value=6), min_size=1, max_size=8))
    @settings(max_examples=80, suppress_health_check=[HealthCheck.too_slow])
    def test_monotonic_headings_no_increment_diag(self, levels: list[int]) -> None:
        # Build a non-skipping heading level sequence.
        clean: list[int] = []
        prev = 0
        for lv in levels:
            nxt = min(lv, prev + 1) if prev else lv
            clean.append(nxt)
            prev = nxt
        headings = [_heading(lv, _text(f"h{lv}")) for lv in clean]
        doc = _doc(*headings)
        diags = list(HeadingIncrementRule().check(LintContext(document=doc)))
        assert diags == []

    @given(words=st.lists(st.text(alphabet="abc XYZ", min_size=1, max_size=10), max_size=10))
    @settings(max_examples=60, suppress_health_check=[HealthCheck.too_slow])
    def test_clean_lines_no_trailing_ws_diag(self, words: list[str]) -> None:
        # Lines whose rstrip() == line produce zero diagnostics.
        lines = [w.rstrip() for w in words]
        src = "\n".join(lines)
        diags = list(TrailingWhitespaceRule().check(LintContext(document=_doc(), source=src)))
        assert diags == []


# =============================================================================
# Thread safety
# =============================================================================


class TestThreadSafety:
    def test_shared_linter_concurrent(self) -> None:
        linter = Linter()  # one shared linter
        sources = {
            "a": "# H1\n\n### H3   ",
            "b": "[](http://x)",
            "c": "clean\n\n## Ok\n",
            "d": "trailing   ",
        }
        expected = {k: linter.lint(v) for k, v in sources.items()}

        barrier = threading.Barrier(len(sources))
        results: dict[str, list[Diagnostic]] = {}

        def work(key: str) -> None:
            barrier.wait()
            results[key] = linter.lint(sources[key])

        with ThreadPoolExecutor(max_workers=len(sources)) as pool:
            list(pool.map(work, list(sources)))

        assert results == expected


# =============================================================================
# Adversarial probes
# =============================================================================


class TestAdversarial:
    def test_heading_nested_in_list_item_no_crash(self) -> None:
        src = "- # Only heading in a list item\n"
        diags = lint(src)
        assert isinstance(diags, list)

    def test_large_source_trailing_ws(self) -> None:
        src = "\n".join("x   " for _ in range(10_000))
        diags = lint(src, rules=[TrailingWhitespaceRule()])
        assert len(diags) == 10_000

    def test_unknown_rule_object_fails_in_registry_not_runner(self) -> None:
        class Bogus:
            pass

        with pytest.raises(TypeError):
            LintRuleRegistryBuilder().register(Bogus())  # type: ignore[arg-type]

    def test_document_root_end_lineno_none(self) -> None:
        # Document root has end_lineno=None; code-block exclusion must tolerate it.
        src = "    indented code   \n\ntext   "
        diags = lint(src)
        assert isinstance(diags, list)


# =============================================================================
# Public API lockstep
# =============================================================================


class TestPublicApiLockstep:
    def test_top_level_names_present(self) -> None:
        assert {"lint", "Diagnostic", "LintRule", "Severity"} <= set(patitas.__all__)
        for name in ("lint", "Diagnostic", "LintRule", "Severity"):
            assert hasattr(patitas, name)

    def test_lint_submodule_importable(self) -> None:
        # The top-level `lint` function and the `patitas.linting` submodule have
        # distinct names, so the submodule is reachable via plain attribute access.
        import patitas.linting

        for name in patitas.linting.__all__:
            assert hasattr(patitas.linting, name)


# =============================================================================
# Dogfood: lint the repo's own docs
# =============================================================================


class TestDogfoodDocs:
    def test_docs_lint_without_raising(self) -> None:
        repo_root = Path(__file__).resolve().parent.parent
        docs = sorted((repo_root / "docs").glob("*.md"))
        readme = repo_root / "README.md"
        if readme.exists():
            docs.append(readme)
        assert docs, "expected to find docs to dogfood"
        for path in docs:
            source = path.read_text(encoding="utf-8")
            doc = parse(source, source_file=str(path))
            diags = lint(doc, text=source, source_file=str(path))
            # Must never raise; diagnostics are data, not errors.
            assert isinstance(diags, list)
