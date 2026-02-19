"""Port/Interface for system-wide FinTS configuration repository."""

from abc import ABC, abstractmethod
from uuid import UUID

from swen.infrastructure.banking.fints_config import FinTSConfig


class FinTSConfigRepository(ABC):
    """Abstract repository for system-wide FinTS configuration.

    This port defines the interface for FinTS configuration persistence,
    following hexagonal architecture principles. Implementations handle
    the actual storage mechanism (SQLAlchemy, in-memory for testing, etc.).

    Unlike most repositories in the system, this is NOT user-scoped.
    It manages a single system-wide configuration row.
    """

    @abstractmethod
    async def get_configuration(self) -> FinTSConfig | None:
        """Get current FinTS configuration."""
        ...

    @abstractmethod
    async def save_configuration(
        self,
        config: FinTSConfig,
        admin_user_id: UUID,
    ) -> None:
        """Save complete configuration (create or update)."""
        ...

    @abstractmethod
    async def update_product_id(
        self,
        product_id: str,
        admin_user_id: UUID,
    ) -> None:
        """Update only the Product ID, keeping CSV unchanged."""
        ...

    @abstractmethod
    async def update_csv(
        self,
        csv_content: bytes,
        encoding: str,
        institute_count: int,
        admin_user_id: UUID,
    ) -> None:
        """Update only the CSV data, keeping Product ID unchanged."""
        ...

    @abstractmethod
    async def exists(self) -> bool:
        """Check if configuration exists."""
        ...
