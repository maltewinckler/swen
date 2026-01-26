from swen_ml.data_models import Anchor, Enrichment, Example, NoiseData

from .factory import RepositoryFactory
from .protocols import EmbeddingRepository
from .sqlalchemy import (
    AnchorRepository,
    AnchorTable,
    Base,
    EnrichmentCacheTable,
    EnrichmentRepository,
    ExampleRepository,
    ExampleTable,
    NoiseRepository,
    NoiseTable,
    get_engine,
    get_session,
    get_session_context,
    get_session_maker,
)

__all__ = [
    # Protocols
    "EmbeddingRepository",
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
