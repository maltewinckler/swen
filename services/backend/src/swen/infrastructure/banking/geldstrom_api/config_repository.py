"""Port/Interface for system-wide Geldstrom API configuration repository."""

from abc import ABC, abstractmethod
from uuid import UUID

from swen.infrastructure.banking.geldstrom_api.config import GeldstromApiConfig


class GeldstromApiConfigRepository(ABC):
    """Abstract repository for system-wide Geldstrom API configuration.

    Unlike most repositories in the system, this is NOT user-scoped.
    It manages a single system-wide configuration row.
    """

    @abstractmethod
    async def get_configuration(self) -> GeldstromApiConfig | None:
        """Get current Geldstrom API configuration."""
        ...

    @abstractmethod
    async def save_configuration(
        self,
        config: GeldstromApiConfig,
        admin_user_id: UUID,
    ) -> None:
        """Save complete configuration (create or update)."""
        ...

    @abstractmethod
    async def exists(self) -> bool:
        """Check if configuration exists."""
        ...

    @abstractmethod
    async def activate(self, admin_user_id: UUID) -> None:
        """Set is_active=True."""
        ...

    @abstractmethod
    async def deactivate(self, admin_user_id: UUID) -> None:
        """Set is_active=False."""
        ...

    @abstractmethod
    async def is_active(self) -> bool:
        """Check if configuration exists and is active."""
        ...
