"""Check parallel-scaling results against a minimum-speedup floor.

Fails CI if free-threaded parallel parsing stops scaling — the signature of an
accidental lock or newly-introduced shared mutable state serializing the parser.
Run after:
    python benchmarks/benchmark_parallel.py --json benchmarks/scaling_results.json

This is a *regression* floor, not a performance target: it only catches scaling
collapsing toward 1.0x. It is intentionally generous and skips cleanly when
scaling cannot be measured (GIL-enabled build, or a single-core runner), so it
never produces false failures in environments that can't exhibit speedup.
"""

import json
import sys
from pathlib import Path

# Minimum acceptable best-case speedup across the measured thread counts.
# Real free-threaded runs scale well above this; a regression that serializes
# the parser (lock / shared state) collapses speedup to ~1.0x and trips this.
MIN_SPEEDUP = 1.3


def main() -> int:
    path = Path(__file__).parent / "scaling_results.json"
    if not path.exists():
        print(f"Missing {path}. Run: python benchmarks/benchmark_parallel.py --json {path}")
        return 1

    data = json.loads(path.read_text())
    env = data.get("env", {})
    max_speedup = data.get("max_speedup", 0.0)

    # Scaling is only meaningful on a free-threaded build with >1 core.
    if env.get("gil_enabled", True):
        print("Scaling check skipped: GIL-enabled build (free-threaded scaling not measurable).")
        return 0
    if (env.get("cpu_count") or 1) < 2:
        print(f"Scaling check skipped: single-core runner (cpu_count={env.get('cpu_count')}).")
        return 0

    if max_speedup < MIN_SPEEDUP:
        results = data.get("results", [])
        table = "  ".join(f"{r['threads']}t={r['speedup']:.2f}x" for r in results)
        print(
            "Parallel-scaling floor not met:\n"
            f"  best speedup {max_speedup:.2f}x < {MIN_SPEEDUP}x floor "
            f"(cpu_count={env.get('cpu_count')})\n"
            f"  per-thread: {table}\n"
            "  This usually means an accidental lock or shared mutable state has "
            "serialized the parser."
        )
        return 1

    print(f"Parallel-scaling floor passed: best speedup {max_speedup:.2f}x >= {MIN_SPEEDUP}x.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
