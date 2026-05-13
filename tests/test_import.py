"""Test alembic-squawk."""

import alembic_squawk


def test_import() -> None:
    """Test that the  can be imported."""
    assert isinstance(alembic_squawk.__name__, str)


def test_version() -> None:
    """Test that the version is available."""
    assert isinstance(alembic_squawk.__version__, str)
