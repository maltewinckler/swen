"""ML storage layer.

This module provides:
- `sqlalchemy`: PostgreSQL persistence layer (tables, repositories)

Note: Domain models are in `swen_ml.data_models`.
"""

from swen_ml.data_models import Anchor, Enrichment, Example, NoiseData

from .factory import RepositoryFactory
from .repositories import (
    AnchorRepository,
    EnrichmentRepository,
    ExampleRepository,
    NoiseRepository,
)
from .sqlalchemy import (
    AnchorTable,
    Base,
    EnrichmentCacheTable,
    ExampleTable,
    NoiseTable,
    get_engine,
    get_session,
    get_session_context,
    get_session_maker,
)

__all__ = [
    # Domain models (Pydantic)
    "Anchor",
    "Enrichment",
    "Example",
    "NoiseData",
    # SQLAlchemy tables
    "AnchorTable",
    "Base",
    "EnrichmentCacheTable",
    "ExampleTable",
    "NoiseTable",
    # Database
    "get_engine",
    "get_session",
    "get_session_context",
    "get_session_maker",
    # Repositories
    "AnchorRepository",
    "EnrichmentRepository",
    "ExampleRepository",
    "NoiseRepository",
    "RepositoryFactory",
]
