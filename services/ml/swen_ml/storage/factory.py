from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from .sqlalchemy.repositories.anchor import AnchorRepository
from .sqlalchemy.repositories.enrichment import EnrichmentRepository
from .sqlalchemy.repositories.example import ExampleRepository
from .sqlalchemy.repositories.noise import NoiseRepository


class RepositoryFactory:
    """Factory for creating ML repositories."""

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
