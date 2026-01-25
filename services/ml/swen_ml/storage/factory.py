"""Repository factory for ML storage."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .repositories.anchor import AnchorRepository
from .repositories.enrichment import EnrichmentRepository
from .repositories.example import ExampleRepository
from .repositories.noise import NoiseRepository


class RepositoryFactory:
    """Factory for creating user-scoped ML repositories from a database session."""

    def __init__(self, session: AsyncSession, user_id: UUID):
        self._session = session
        self._user_id = user_id

    @property
    def noise(self) -> NoiseRepository:
        """Get noise model repository."""
        return NoiseRepository(self._session, self._user_id)

    @property
    def example(self) -> ExampleRepository:
        """Get example embeddings repository."""
        return ExampleRepository(self._session, self._user_id)

    @property
    def anchor(self) -> AnchorRepository:
        """Get anchor embeddings repository."""
        return AnchorRepository(self._session, self._user_id)

    def enrichment(self, ttl_days: int = 30) -> EnrichmentRepository:
        """Get enrichment cache repository."""
        return EnrichmentRepository(self._session, ttl_days)
