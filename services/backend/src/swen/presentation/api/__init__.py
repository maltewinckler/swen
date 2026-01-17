"""REST API presentation layer for SWEN.

This package provides a FastAPI-based REST API for the SWEN application.

Structure:
    api/
    ├── app.py          # FastAPI application factory
    ├── config.py       # API configuration
    ├── dependencies.py # Dependency injection
    ├── routers/        # API route handlers
    └── schemas/        # Pydantic request/response schemas

Usage:
    # For uvicorn
    uvicorn swen.presentation.api.app:app

    # For importing the factory directly
    from swen.presentation.api.app import create_app
"""
