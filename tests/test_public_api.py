"""Pin the public API surface of the top-level ``patitas`` package.

The public API (everything in ``patitas.__all__``) is the 1.0 stability
contract. These tests fail CI if a public symbol is accidentally added or
removed, forcing the change to be deliberate (and ``docs/public-api.md`` to be
updated alongside it).

See ``docs/public-api.md`` for the documented boundary between the supported
public API and internal modules.
"""

import patitas

# The exact, deliberate set of public symbols. Update this set ONLY when you
# also update docs/public-api.md and intend to change the public API.
EXPECTED_PUBLIC_API: frozenset[str] = frozenset(
    {
        # Version
        "__version__",
        # Core API
        "parse",
        "parse_notebook",
        "render",
        # Parse cache
        "DictParseCache",
        "ParseCache",
        "hash_config",
        "hash_content",
        # Block nodes
        "Block",
        "BlockQuote",
        "Document",
        "FencedCode",
        "FootnoteDef",
        "Heading",
        "HtmlBlock",
        "IndentedCode",
        "List",
        "ListItem",
        "MathBlock",
        "Paragraph",
        "Table",
        "TableCell",
        "TableRow",
        "ThematicBreak",
        # Inline nodes
        "Inline",
        "CodeSpan",
        "Emphasis",
        "FootnoteRef",
        "HtmlInline",
        "Image",
        "LineBreak",
        "Link",
        "Math",
        "Role",
        "SoftBreak",
        "Strikethrough",
        "Strong",
        "Text",
        # Directive extensibility
        "Directive",
        "DirectiveRegistry",
        "DirectiveRegistryBuilder",
        "create_default_registry",
        "create_registry_with_defaults",
        "directive",
        # Roles
        "RoleHandler",
        "RoleRegistry",
        "RoleRegistryBuilder",
        "create_default_role_registry",
        # Parser components
        "Lexer",
        "Parser",
        # Renderer
        "HtmlRenderer",
        "LlmRenderer",
        "ASTRenderer",
        "render_llm",
        # Text extraction
        "extract_text",
        # Linting
        "lint",
        "Diagnostic",
        "LintRule",
        "Severity",
        # Sanitization
        "sanitize",
        "Policy",
        # Visitor + Transform
        "BaseVisitor",
        "transform",
        # Differ
        "ASTChange",
        "diff_documents",
        # Excerpt
        "extract_excerpt",
        "extract_meta_description",
        # Frontmatter
        "parse_frontmatter",
        "extract_body",
        # Incremental
        "parse_incremental",
        # Context mapping
        "CONTENT_CONTEXT_MAP",
        "context_paths_for",
        # Profiling
        "ParseAccumulator",
        "profiled_parse",
        "get_parse_accumulator",
        # Serialization
        "to_dict",
        "from_dict",
        "to_json",
        "from_json",
        # Configuration (ContextVar-based)
        "ParseConfig",
        "get_parse_config",
        "set_parse_config",
        "reset_parse_config",
        "parse_config_context",
        # Location
        "SourceLocation",
        # Tokens
        "Token",
        "TokenType",
        # High-level
        "Markdown",
    }
)


def test_all_matches_expected_public_api() -> None:
    """patitas.__all__ must match the pinned expected set exactly.

    Any accidental addition/removal of a public symbol fails here.
    """
    actual = set(patitas.__all__)
    missing = EXPECTED_PUBLIC_API - actual
    extra = actual - EXPECTED_PUBLIC_API
    assert not missing, f"Public symbols removed from __all__: {sorted(missing)}"
    assert not extra, f"Unexpected new public symbols in __all__: {sorted(extra)}"


def test_all_has_no_duplicates() -> None:
    """__all__ should not contain duplicate entries."""
    assert len(patitas.__all__) == len(set(patitas.__all__))


def test_every_public_name_is_importable() -> None:
    """Every name in __all__ must be an attribute of the patitas package."""
    for name in patitas.__all__:
        assert hasattr(patitas, name), f"{name!r} in __all__ but not importable from patitas"


def test_role_api_is_public() -> None:
    """The role API promoted in issue #29 must be part of the public surface."""
    for name in (
        "RoleHandler",
        "RoleRegistry",
        "RoleRegistryBuilder",
        "create_default_role_registry",
    ):
        assert name in patitas.__all__
        assert hasattr(patitas, name)


def test_lint_api_is_public() -> None:
    """The lint API added in issue #56 must be part of the public surface."""
    for name in (
        "lint",
        "Diagnostic",
        "LintRule",
        "Severity",
    ):
        assert name in patitas.__all__
        assert hasattr(patitas, name)
