"""Account hierarchy domain service."""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional, Set
from uuid import UUID

from swen.domain.accounting.entities import Account
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.shared.exceptions import ValidationError

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class AccountHierarchyService:
    """Validate and inspect account parent-child relationships."""

    def __init__(self, account_repo: AccountRepository):
        self._account_repo = account_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> AccountHierarchyService:
        account_repository = factory.account_repository()
        return cls(account_repo=account_repository)

    async def validate_hierarchy(self, child: Account, parent: Account) -> None:
        """Validate parent-child constraints (cycle, depth, type, ownership)."""
        # Check circular reference
        if await self._would_create_cycle(child.id, parent.id):
            msg = "Setting parent would create circular reference"
            raise ValidationError(msg)

        # Check depth
        depth = await self._get_account_depth(parent.id)
        if depth >= 2:  # Max 3 levels: root -> parent -> child
            msg = "Maximum hierarchy depth (3 levels) would be exceeded"
            raise ValidationError(msg)

    async def can_delete(self, account: Account) -> bool:
        return not await self._account_repo.is_parent(account.id)

    async def get_all_descendants(self, account_id: UUID) -> List[Account]:
        return await self._account_repo.find_descendants(account_id)

    async def is_parent(self, account_id: UUID) -> bool:
        return await self._account_repo.is_parent(account_id)

    async def _would_create_cycle(
        self,
        child_id: UUID,
        new_parent_id: UUID,
    ) -> bool:
        visited: Set[UUID] = {child_id}
        current_id = new_parent_id

        while current_id:
            if current_id in visited:
                return True

            visited.add(current_id)
            account = await self._account_repo.find_by_id(current_id)
            if not account:
                break
            current_id = account.parent_id

        return False

    async def _get_account_depth(self, account_id: UUID) -> int:
        depth = 0
        current_id: Optional[UUID] = account_id

        while current_id:
            account = await self._account_repo.find_by_id(current_id)
            if not account or not account.parent_id:
                break
            depth += 1
            current_id = account.parent_id

        return depth
