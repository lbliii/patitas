"""JIT experiment: compare Patitas with and without Python's experimental JIT.

Run:
    PYTHONPATH=src python benchmarks/experiment_jit.py          # no JIT
    PYTHONPATH=src python -X jit benchmarks/experiment_jit.py   # with JIT
"""

import json
import sys
import time
from pathlib import Path


def get_corpus() -> list[str]:
    spec = Path(__file__).parent.parent / "tests" / "fixtures" / "commonmark_spec_0_31_2.json"
    return [ex["markdown"] for ex in json.loads(spec.read_text())]


def bench_patitas(docs: list[str], iters: int = 10) -> float:
    from patitas import Markdown

    md = Markdown()
    for d in docs[:10]:
        md(d)
    start = time.perf_counter()
    for _ in range(iters):
        for d in docs:
            md(d)
    return (time.perf_counter() - start) / iters * 1000


def main() -> None:
    docs = get_corpus()
    print(f"Python: {sys.version.split()[0]}")
    print(f"Corpus: {len(docs)} docs")
    print()

    # Warmup (JIT needs this to compile hot paths)
    _ = bench_patitas(docs)

    times = [bench_patitas(docs) for _ in range(8)]
    avg = sum(times) / len(times)
    print(f"Patitas (8 runs): {[f'{t:.2f}ms' for t in times]}")
    print(f"Average: {avg:.2f}ms")


if __name__ == "__main__":
    main()
