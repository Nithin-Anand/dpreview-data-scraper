"""Shared test fixtures."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent


@pytest.fixture
def fixtures_dir():
    """Return the base fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def camera_list_html(fixtures_dir):
    """Load the default camera list HTML fixture."""
    return (fixtures_dir / "fixtures" / "camera_list.html").read_text(encoding="utf-8")


@pytest.fixture
def camera_list_last_html(fixtures_dir):
    """Load the last-page camera list HTML fixture (may lack next link)."""
    return (fixtures_dir / "fixtures_last" / "camera_list.html").read_text(encoding="utf-8")


@pytest.fixture
def product_overview_html(fixtures_dir):
    """Load the default product overview HTML fixture (Sony a7 V)."""
    return (fixtures_dir / "fixtures" / "product_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def product_specs_html(fixtures_dir):
    """Load the product specifications HTML fixture (Sony a7 V)."""
    return (fixtures_dir / "fixtures_specs" / "product_sample.html").read_text(encoding="utf-8")
