# Security

Patitas is designed to **resist denial-of-service from untrusted input**: the
lexer is a hand-written finite state machine (no catastrophic regex
backtracking), and block-container nesting is bounded (see
[Nesting limits](#nesting-limits)).

> **Important:** Patitas does **not** sanitize HTML or URLs by default. The
> default `render()` is CommonMark-compliant and passes raw HTML and
> `javascript:`/`data:` URLs through verbatim. For untrusted *output*, use
> [`sanitize()`](#output-sanitization) or `render_llm()`. See
> [Output sanitization](#output-sanitization) below.

## ReDoS Resistance

Regular Expression Denial of Service (ReDoS) is a class of vulnerability where carefully crafted input causes regex engines to enter catastrophic backtracking, consuming CPU for seconds, minutes, or longer.

**Patitas does not use backtracking regular expressions in its lexer, so it is
not vulnerable to the catastrophic-backtracking ReDoS that affects regex-based
parsers.** (This is not the same as "immune to all denial of service" — see
[Known limitations](#known-limitations).)

### The Problem with Regex-Based Parsers

Most Markdown parsers use regular expressions for pattern matching. Regex engines using backtracking can be exploited:

```python
# Example: Link parsing regex vulnerable to backtracking
pattern = r'\[([^\]]*)\]\(([^)]*)\)'

# Malicious input that triggers exponential backtracking
evil_input = "[" + "a" * 50 + "](" + "\\)" * 50
```

This affects popular parsers including mistune, Python-Markdown, and markdown-it-py.

### Real-World Impact

ReDoS vulnerabilities have caused production outages:

- **Cloudflare (2019)**: Regex in WAF rules caused global outage
- **Stack Overflow (2016)**: Regex in post rendering caused site slowdown
- **npm (various)**: Multiple packages with ReDoS in markdown/text processing

### How Patitas Avoids ReDoS

Patitas uses a **hand-written finite state machine lexer** instead of regex:

```
┌─────────┐   char    ┌─────────┐   char    ┌─────────┐
│ INITIAL │ ────────► │  STATE  │ ────────► │  STATE  │
│  STATE  │           │    A    │           │    B    │
└─────────┘           └─────────┘           └─────────┘
     │                     │                     │
     │ emit                │ emit                │ emit
     ▼                     ▼                     ▼
 [Token]               [Token]               [Token]
```

**Key properties of the lexer:**

1. **Single character lookahead** — The lexer examines at most one character ahead
2. **No backtracking** — Once a character is consumed, we never revisit it
3. **Linear lexing** — Tokenization time is linear in input length
4. **No catastrophic-backtracking regex** — The vulnerable pattern class is absent

<a name="nesting-limits"></a>
## Nesting limits

Deeply nested block containers (block quotes, lists, directives) are bounded by
`max_nesting_depth` (default **100**). Input that exceeds the limit raises a
catchable `patitas.errors.ParseError` instead of crashing the interpreter with an
uncaught `RecursionError`:

```python
from patitas import Markdown
from patitas.errors import ParseError

md = Markdown(max_nesting_depth=100)  # configurable
deeply_nested = "".join("  " * i + "- x\n" for i in range(500))
try:
    md(deeply_nested)
except ParseError:
    ...  # rejected cleanly, not a crash
```

<a name="known-limitations"></a>
## Known limitations

The lexer is backtracking-free, but a few non-lexer paths are not yet fully
hardened against adversarial input (tracked in the project's "adversarial input
hardening" issue):

- **Inline bracket scan is O(n²)** — pathological inputs such as `"[" * N` take
  quadratic time. Cap input size for untrusted callers.
- **Inline emphasis nesting** — extremely deep delimiter runs (e.g. `"*" * N`)
  can exhaust the stack during rendering.
- **Single-line `>` markers** — thousands of `>` on one line recurse in the
  lexer before the nesting guard applies.

Until these are closed, treat **input-size limits and timeouts** as required
defense-in-depth (see [Recommendations](#recommendations)).

<a name="output-sanitization"></a>
## Output sanitization

The default `render()` is **CommonMark-compliant and does not sanitize output**:
raw HTML and `javascript:`/`data:` URLs pass through verbatim, exactly like
markdown-it-py with `html: true`. This is by design — sanitization is a separate,
explicit step.

For untrusted content, sanitize the AST before rendering, or render to plain text:

```python
from patitas import parse, sanitize, render, render_llm
from patitas.sanitize import web_safe

doc = parse(untrusted_markdown)

# Option A: strip HTML + disallowed URL schemes, then render HTML
html = render(sanitize(doc, policy=web_safe))

# Option B: render to LLM-safe plain text (no HTML at all)
text = render_llm(doc)
```

`web_safe`/`llm_safe`/`strict` use an **allow-list** of URL schemes
(`https`, `http`, `mailto`; relative/fragment URLs kept) and see through
obfuscated schemes (entity-encoded, embedded whitespace, mixed case). Compose
custom policies with `allow_url_schemes(...)`, `strip_html`, `normalize_unicode`,
`limit_depth(...)`, and the `|` operator.

## Recommendations

For applications processing untrusted markdown:

1. **Limit input size** — the single most effective mitigation for DoS
2. **Set timeouts** — defense in depth for any parser
3. **Sanitize output** — use `sanitize()`/`render_llm()`; the default renderer does not
4. **Keep `max_nesting_depth` at a sane value** — the default (100) is well above real content

## Reporting Vulnerabilities

If you discover a security issue in Patitas:

1. **Do not** open a public GitHub issue
2. Email security concerns to the maintainers
3. Allow time for a fix before public disclosure

We take security seriously and will respond promptly to any reports.
