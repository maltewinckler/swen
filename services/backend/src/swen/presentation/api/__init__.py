"""REST API presentation layer for SWEN.

This package provides a FastAPI-based REST API for the SWEN application.

Structure:
    api/
    ├── app.py          # FastAPI application factory
    ├── config.py       # API configuration
    ├── dependencies.py # Dependency injection
    ├── routers/        # API route handlers
    └── schemas/        # Pydantic request/response schemas
"""

from swen.presentation.api.app import create_app

__all__ = ["create_app"]
