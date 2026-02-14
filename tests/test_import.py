"""Verify package imports work correctly."""


def test_import_patitas() -> None:
    """Test that patitas can be imported and version matches pyproject."""
    import tomllib
    from pathlib import Path

    import patitas

    with (Path(__file__).resolve().parent.parent / "pyproject.toml").open("rb") as f:
        expected = tomllib.load(f)["project"]["version"]
    assert patitas.__version__ == expected


def test_version_format() -> None:
    """Test version string format."""
    from patitas import __version__

    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
