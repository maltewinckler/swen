"""Shared fixtures for AI integration tests."""

import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "ollama: mark test as requiring Ollama"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )

