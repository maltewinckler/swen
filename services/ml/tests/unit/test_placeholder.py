"""Placeholder test to ensure test collection works.

TODO: Add proper unit tests for the new ML pipeline.
"""


def test_placeholder() -> None:
    """Placeholder test - ML package is importable."""
    from swen_ml.api.app import create_app

    app = create_app()
    assert app.title == "SWEN ML Service"
