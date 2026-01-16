"""
Configuration for external service tests (real bank connections).

These tests require real credentials and network access.
They are skipped by default unless explicitly enabled.

Enable with: --run-external or RUN_EXTERNAL=1
"""

import os
from dataclasses import dataclass

import pytest


@dataclass
class BankCredentials:
    """Bank credentials loaded from environment."""

    blz: str
    username: str
    pin: str
    endpoint: str


def _load_credentials() -> BankCredentials | None:
    """Load credentials from environment variables."""
    blz = os.environ.get("FINTS_BLZ")
    username = os.environ.get("FINTS_USERNAME")
    pin = os.environ.get("FINTS_PIN")
    endpoint = os.environ.get("FINTS_ENDPOINT")

    if not all([blz, username, pin, endpoint]):
        return None

    # Type narrowing: we've verified none are None above
    assert blz is not None
    assert username is not None
    assert pin is not None
    assert endpoint is not None

    return BankCredentials(
        blz=blz,
        username=username,
        pin=pin,
        endpoint=endpoint,
    )


def pytest_addoption(parser):
    """Add --run-external command line option."""
    parser.addoption(
        "--run-external",
        action="store_true",
        default=False,
        help="Run tests that connect to external services (real banks)",
    )


def pytest_configure(config):
    """Register external test marker."""
    config.addinivalue_line(
        "markers",
        "external: Tests that connect to real external services (auto-skipped)",
    )


def pytest_collection_modifyitems(config, items):
    """
    Auto-skip external tests unless explicitly enabled.

    Enable with: --run-external or RUN_EXTERNAL=1
    """
    run_external = config.getoption("--run-external") or os.environ.get(
        "RUN_EXTERNAL",
        "",
    ).lower() in ("1", "true", "yes")

    if run_external:
        return

    skip_external = pytest.mark.skip(
        reason="External tests disabled. Run with --run-external or RUN_EXTERNAL=1",
    )

    for item in items:
        # Skip all tests in tests/external/ directory
        if "/external/" in str(item.fspath):
            item.add_marker(skip_external)


@pytest.fixture(scope="session")
def bank_credentials():
    """
    Provide bank credentials for external tests.

    Skips tests if credentials are not configured.
    """
    creds = _load_credentials()
    if creds is None:
        pytest.skip(
            "Bank credentials not configured. "
            "Set FINTS_BLZ, FINTS_USERNAME, FINTS_PIN, FINTS_ENDPOINT in .env",
        )
    return creds
