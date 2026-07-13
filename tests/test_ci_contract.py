"""Executable ratchets for Patitas CI and release readiness."""

import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(
    not (ROOT / ".github/workflows").is_dir(),
    reason="repository-only CI contract metadata is not shipped in sdists",
)


def test_coverage_floor_is_at_least_eighty_percent() -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["tool"]["coverage"]["report"]["fail_under"] >= 80


def test_required_ci_has_gil_and_free_threaded_lanes() -> None:
    workflow = (ROOT / ".github/workflows/tests.yml").read_text(encoding="utf-8")

    assert 'python-version: "3.14"' in workflow
    assert 'python-version: "3.14t"' in workflow
    assert 'python-gil: "1"' in workflow
    assert 'python-gil: "0"' in workflow
    assert "PYTHON_GIL: ${{ matrix.python-gil }}" in workflow
    assert "--cov-fail-under=80" in workflow
    assert "--cov-fail-under=67" not in workflow


def test_publish_waits_for_dual_interpreter_release_gate() -> None:
    workflow = (ROOT / ".github/workflows/python-publish.yml").read_text(encoding="utf-8")
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "release-gate:" in workflow
    assert 'python-version: "3.14"' in workflow
    assert 'python-version: "3.14t"' in workflow
    assert "needs:\n      - release-gate" in workflow
    assert "run: make release-gate" in workflow
    assert "publish: release-gate" in makefile
    assert 'pytest -n auto -q --tb=short --dist worksteal -m "not slow"' in makefile
    assert 'pytest -n 0 -q --tb=short -m "slow"' in makefile
