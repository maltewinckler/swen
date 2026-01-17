"""Root pytest configuration for test discovery and auto-skip behavior.

This conftest.py makes all tests visible in VS Code test explorer while
auto-skipping slow/manual tests unless explicitly enabled via environment
variables or pytest options.

Test Structure:
    tests/
    ├── swen/                  # Core domain tests (banking, accounting)
    │   ├── unit/              # Fast, isolated tests
    │   └── integration/       # Tests with Testcontainers PostgreSQL
    ├── swen_identity/         # Identity domain tests (users, auth)
    │   ├── unit/
    │   └── integration/
    ├── cross_domain/          # Tests spanning multiple domains
    │   ├── integration/
    │   └── e2e/
    ├── external/              # Real bank tests (requires credentials)
    │   ├── fints/
    │   └── tan/
    └── shared/                # Shared fixtures and utilities

Environment Variables:
    RUN_INTEGRATION=1    Run @pytest.mark.integration tests
    RUN_MANUAL_TAN=1     Run @pytest.mark.tan and @pytest.mark.manual tests
    RUN_EXTERNAL=1       Run external bank tests (requires credentials)
    RUN_ALL_TESTS=1      Run all tests (overrides other settings)

Pytest Options:
    --run-integration    Run integration tests
    --run-manual         Run manual/TAN tests
    --run-external       Run external bank tests
    --run-all            Run all tests
"""

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from swen_config import clear_settings_cache

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load .env.dev for tests (same as local development)
CONFIG_DIR = PROJECT_ROOT.parent.parent / "config"
if (CONFIG_DIR / ".env.dev").exists():
    load_dotenv(CONFIG_DIR / ".env.dev")
elif (CONFIG_DIR / ".env").exists():
    load_dotenv(CONFIG_DIR / ".env")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run tests marked with @pytest.mark.integration",
    )
    parser.addoption(
        "--run-manual",
        action="store_true",
        default=False,
        help="Run tests marked with @pytest.mark.manual or @pytest.mark.tan",
    )
    parser.addoption(
        "--run-all",
        action="store_true",
        default=False,
        help="Run all tests regardless of markers",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: Tests that verify database/persistence behavior (auto-skipped)",
    )
    config.addinivalue_line(
        "markers",
        "manual: Tests requiring manual intervention (auto-skipped)",
    )
    config.addinivalue_line(
        "markers",
        "tan: Tests requiring TAN approval (auto-skipped)",
    )
    config.addinivalue_line(
        "markers",
        "external: Tests connecting to real external services (auto-skipped)",
    )
    config.addinivalue_line(
        "markers",
        "slow: Tests that take more than 1 second",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-skip tests based on markers unless explicitly enabled.

    This approach makes all tests visible in VS Code test explorer
    while still skipping slow/manual tests by default.
    """
    # Check for "run all" flags
    run_all = config.getoption("--run-all") or os.environ.get(
        "RUN_ALL_TESTS",
        "",
    ).lower() in ("1", "true", "yes")

    if run_all:
        return  # Don't skip anything

    # Check individual flags
    run_integration = config.getoption("--run-integration") or os.environ.get(
        "RUN_INTEGRATION",
        "",
    ).lower() in ("1", "true", "yes")

    run_manual = config.getoption("--run-manual") or os.environ.get(
        "RUN_MANUAL_TAN",
        "",
    ).lower() in ("1", "true", "yes")

    # Define skip reasons
    skip_integration = pytest.mark.skip(
        reason="Integration test - run with --run-integration or RUN_INTEGRATION=1",
    )
    skip_manual = pytest.mark.skip(
        reason="Manual/TAN test - run with --run-manual or RUN_MANUAL_TAN=1",
    )

    for item in items:
        # Get actual markers on the item (not just keyword matches)
        item_markers = {mark.name for mark in item.iter_markers()}

        # Check for integration marker (explicit marker only, not folder name)
        if not run_integration and "integration" in item_markers:
            item.add_marker(skip_integration)

        # Check for manual or tan markers
        if not run_manual and ("manual" in item_markers or "tan" in item_markers):
            item.add_marker(skip_manual)


@pytest.fixture(scope="session", autouse=True)
def configure_app_settings():
    """Ensure settings are loaded from .env files for tests.

    Tests use config/.env.dev (local development settings).
    The .env file is loaded at module import time via load_dotenv above.
    """
    # Clear any cached settings to ensure fresh load
    clear_settings_cache()
    yield
    clear_settings_cache()
