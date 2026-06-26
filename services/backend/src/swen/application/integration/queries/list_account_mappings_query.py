"""List account mappings query - retrieve account mappings for display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from swen.application.integration.dtos import (
    AccountMappingDTO,
    AccountMappingListDTO,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.repositories import AccountRepository
    from swen.domain.integration.entities import AccountMapping
    from swen.domain.integration.repositories import AccountMappingRepository


class ListAccountMappingsQuery:
    """Query to list account mappings with resolved account info."""

    def __init__(
        self,
        mapping_repository: AccountMappingRepository,
        account_repository: AccountRepository,
    ):
        self._mapping_repo = mapping_repository
        self._account_repo = account_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListAccountMappingsQuery:
        return cls(
            mapping_repository=factory.account_mapping_repository(),
            account_repository=factory.account_repository(),
        )

    async def _dto_from_mapping(self, mapping: AccountMapping) -> AccountMappingDTO:
        id_ = mapping.accounting_account_id
        account = await self._account_repo.find_by_id(id_)
        account_name = account.name if account else None
        account_number = account.account_number if account else None
        return AccountMappingDTO(
            id=mapping.id,
            iban=mapping.iban,
            account_name=mapping.account_name,
            accounting_account_id=id_,
            accounting_account_name=account_name,
            accounting_account_number=account_number,
            created_at=mapping.created_at.isoformat(),
        )

    async def execute(self) -> AccountMappingListDTO:
        """List all account mappings with resolved account info.

        Returns
        -------
            AccountMappingListDTO containing all mappings with their
            associated accounting account details.
        """
        mappings = await self._mapping_repo.find_all()
        dtos = [await self._dto_from_mapping(mapping) for mapping in mappings]

        return AccountMappingListDTO(
            mappings=dtos,
            count=len(dtos),
        )

    async def get_by_iban(self, iban: str) -> Optional[AccountMappingDTO]:
        """Get a single account mapping by IBAN.

        Returns
        -------
            AccountMappingDTO if found, None otherwise.
        """
        mapping = await self._mapping_repo.find_by_iban(iban)
        if not mapping:
            return None

        return await self._dto_from_mapping(mapping)
