"""Check benchmark results against performance thresholds.

Fails CI if key benchmarks regress beyond acceptable limits.
Run after: pytest benchmarks/... --benchmark-only --benchmark-json=benchmarks/ci_results.json

Thresholds are mean time in milliseconds. 1.5× headroom over current baselines.
"""

import json
import sys
from pathlib import Path

# test_name -> max mean (ms). Fail if benchmark exceeds.
THRESHOLDS_MS: dict[str, float] = {
    "test_benchmark_parse_10kb": 25,
    "test_benchmark_parse_100kb": 200,
    "test_benchmark_parse_500kb": 1000,
    "test_benchmark_parse_list_table_50kb": 150,
    "test_benchmark_parse_only_10kb": 20,
    "test_benchmark_parse_only_500kb": 1000,
    "test_benchmark_extract_excerpt_code_heavy": 50,
    "test_benchmark_extract_excerpt_commonmark": 1500,
}


def main() -> int:
    path = Path(__file__).parent / "ci_results.json"
    if not path.exists():
        print(f"Missing {path}. Run benchmarks with --benchmark-json=benchmarks/ci_results.json")
        return 1

    data = json.loads(path.read_text())
    benchmarks = {b["name"]: b for b in data.get("benchmarks", [])}

    failed: list[str] = []
    missing: list[str] = []
    for name, max_ms in THRESHOLDS_MS.items():
        if name not in benchmarks:
            missing.append(name)
            continue
        mean_s = benchmarks[name]["stats"]["mean"]
        mean_ms = mean_s * 1000
        if mean_ms > max_ms:
            failed.append(f"  {name}: {mean_ms:.1f}ms > {max_ms}ms threshold")

    if missing:
        print("Missing required benchmarks (run full suite):\n  " + "\n  ".join(missing))
        return 1
    if failed:
        print("Benchmark thresholds exceeded:\n" + "\n".join(failed))
        return 1
    print("All benchmark thresholds passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
