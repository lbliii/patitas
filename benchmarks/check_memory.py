"""Check memory results against a per-doc retained-footprint ceiling.

Fails CI if the parsed-AST memory footprint per document regresses sharply —
the signature of fatter AST nodes, a retained-reference leak, or accidental
duplication. Run after:
    python benchmarks/memory_bench.py --json benchmarks/memory_results.json

This is a generous *regression* ceiling, not a tight target. The render phase's
transient peak is reported by the benchmark for visibility but is not gated
(a single peak is not a meaningful per-doc figure).
"""

import json
import sys
from pathlib import Path

# Max retained AST bytes per document. Observed ~900 B/doc on the CommonMark
# corpus; the 2x headroom catches a real regression (node bloat / leak) without
# tripping on build-to-build object-size differences (e.g. free-threading).
MAX_PARSE_BYTES_PER_DOC = 2000.0


def main() -> int:
    path = Path(__file__).parent / "memory_results.json"
    if not path.exists():
        print(f"Missing {path}. Run: python benchmarks/memory_bench.py --json {path}")
        return 1

    data = json.loads(path.read_text())
    parse_bpd = data.get("parse", {}).get("retained_bytes_per_doc")
    if parse_bpd is None:
        print("Memory results missing parse.retained_bytes_per_doc.")
        return 1

    if parse_bpd > MAX_PARSE_BYTES_PER_DOC:
        print(
            "Memory regression: retained AST footprint exceeds ceiling:\n"
            f"  parse: {parse_bpd:.0f} B/doc > {MAX_PARSE_BYTES_PER_DOC:.0f} B/doc "
            f"(docs={data.get('docs')})"
        )
        return 1

    render_peak = data.get("render", {}).get("peak_bytes")
    extra = f"; render peak {render_peak / 1024:.1f} KiB" if render_peak is not None else ""
    print(
        f"Memory check passed: parse {parse_bpd:.0f} B/doc <= {MAX_PARSE_BYTES_PER_DOC:.0f}{extra}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
