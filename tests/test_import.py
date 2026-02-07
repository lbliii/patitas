"""Verify package imports work correctly."""


def test_import_patitas() -> None:
    """Test that patitas can be imported."""
    import patitas

    assert patitas.__version__ == "0.1.0"


def test_version_format() -> None:
    """Test version string format."""
    from patitas import __version__

    parts = __version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
