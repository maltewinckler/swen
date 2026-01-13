from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PasswordResetTokenData:
    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    def is_expired(self, now: datetime) -> bool:
        return now > self.expires_at

    def is_used(self) -> bool:
        return self.used_at is not None


class PasswordResetTokenRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> UUID:
        pass

    @abstractmethod
    async def find_valid_by_hash(self, token_hash: str) -> PasswordResetTokenData | None:
        pass

    @abstractmethod
    async def mark_used(self, token_id: UUID) -> None:
        pass

    @abstractmethod
    async def invalidate_all_for_user(self, user_id: UUID) -> None:
        pass

    @abstractmethod
    async def count_recent_for_user(self, user_id: UUID, since: datetime) -> int:
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        pass
