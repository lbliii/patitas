# Security

Patitas is designed to be **safe for untrusted input**.

## ReDoS Immunity

Regular Expression Denial of Service (ReDoS) is a class of vulnerability where carefully crafted input causes regex engines to enter catastrophic backtracking, consuming CPU for seconds, minutes, or longer.

**Patitas is immune to ReDoS attacks.**

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

**Key properties:**

1. **Single character lookahead** — The lexer examines at most one character ahead
2. **No backtracking** — Once a character is consumed, we never revisit it
3. **O(n) guaranteed** — Processing time is strictly linear with input length
4. **Constant memory per character** — No recursive state or stack growth

### Proof of Safety

For any input of length `n`:

- **Time complexity**: O(n) — Each character examined exactly once
- **Space complexity**: O(n) — AST grows linearly with content
- **No input can cause superlinear behavior**

### Testing

We test with adversarial inputs designed to trigger ReDoS in regex-based parsers:

```python
def test_redos_immunity():
    """Verify malicious inputs complete in linear time."""
    from patitas import parse
    import time
    
    # Input that causes exponential backtracking in regex parsers
    evil = "a](" + "\\)" * 10000
    
    start = time.perf_counter()
    parse(evil)
    elapsed = time.perf_counter() - start
    
    # Must complete in under 100ms regardless of payload size
    assert elapsed < 0.1
```

## Safe Defaults

Patitas follows secure defaults:

| Feature | Default | Notes |
|---------|---------|-------|
| HTML rendering | Escaped | Raw HTML requires explicit opt-in |
| Link URLs | Encoded | Special characters percent-encoded |
| Script injection | Blocked | `javascript:` URLs not rendered as links |

## Recommendations

For applications processing untrusted markdown:

1. **Use Patitas** — ReDoS-proof by design
2. **Set timeouts** — Defense in depth for any parser
3. **Limit input size** — Prevent memory exhaustion
4. **Sanitize output** — Additional HTML sanitization if needed

## Reporting Vulnerabilities

If you discover a security issue in Patitas:

1. **Do not** open a public GitHub issue
2. Email security concerns to the maintainers
3. Allow time for a fix before public disclosure

We take security seriously and will respond promptly to any reports.
