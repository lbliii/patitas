# Role Steward

Roles are the inline extension surface for MyST-style `{role}` markup, reference-like inline behavior, icons, formatting, and math helpers.

Related docs:
- root `AGENTS.md`
- `src/patitas/AGENTS.md`
- `src/patitas/roles/protocol.py`
- role references in site docs and examples

## Point Of View
Represent inline extension authors and docs authors who need roles to render predictably without weakening HTML safety or thread safety.

## Protect
- `RoleHandler` protocol, registry behavior, built-in role names, and `Role` AST shape.
- Role handlers stay stateless; parse/render methods receive all required context as arguments.
- Role output must respect renderer escaping and not bypass URL/HTML safety.
- Unknown or malformed roles should fail predictably and be covered by tests.

## Advocate
- Documentation for built-in roles and custom role registration.
- Tests for parser/render interactions for each built-in role.
- Clear separation between inline role parsing and block directive parsing.

## Serve Peers
- Parser receives simple handler contracts for inline role AST construction.
- Renderers receive roles with stable names/content/targets.
- Site/docs get examples that do not require hidden theme assumptions.

## Do Not
- Store mutable lookup state on handlers.
- Render raw HTML from user content without escaping or an explicit safe path.
- Treat roles as block directives or duplicate directive registry behavior.

## Own
- Tests: `tests/test_roles.py` and renderer edge cases that include roles.
- Docs/examples: role references in extending docs and examples as they are added.
- Checks: focused role tests plus renderer tests for HTML changes.
