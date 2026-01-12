"""List account mappings query - retrieve account mappings for display."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

from swen.application.dtos.export_dto import MappingExportDTO
from swen.domain.accounting.entities import Account
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.repositories import AccountMappingRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


@dataclass
class MappingWithAccount:
    """Account mapping with resolved account."""

    mapping: AccountMapping
    account: Optional[Account] = None


@dataclass
class AccountMappingListResult:
    """Result of listing account mappings."""

    mappings: list[AccountMapping]
    total_count: int


class ListAccountMappingsQuery:
    """Query to list account mappings."""

    def __init__(
        self,
        mapping_repository: AccountMappingRepository,
        account_repository: Optional[AccountRepository] = None,
    ):
        self._mapping_repo = mapping_repository
        self._account_repo = account_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListAccountMappingsQuery:
        return cls(
            mapping_repository=factory.account_mapping_repository(),
            account_repository=factory.account_repository(),
        )

    async def execute(self) -> AccountMappingListResult:
        mappings = await self._mapping_repo.find_all()
        return AccountMappingListResult(
            mappings=mappings,
            total_count=len(mappings),
        )

    async def find_by_iban(self, iban: str) -> Optional[AccountMapping]:
        return await self._mapping_repo.find_by_iban(iban)

    async def get_mapping_with_account(
        self,
        iban: str,
    ) -> Optional[MappingWithAccount]:
        mapping = await self._mapping_repo.find_by_iban(iban)
        if not mapping:
            return None

        account = None
        if self._account_repo:
            account = await self._account_repo.find_by_id(mapping.accounting_account_id)

        return MappingWithAccount(mapping=mapping, account=account)

    async def get_all_with_accounts(self) -> list[MappingWithAccount]:
        mappings = await self._mapping_repo.find_all()
        results = []

        for mapping in mappings:
            account = None
            if self._account_repo:
                account = await self._account_repo.find_by_id(
                    mapping.accounting_account_id,
                )
            results.append(MappingWithAccount(mapping=mapping, account=account))

        return results

    async def get_mappings_for_export(self) -> list[MappingExportDTO]:
        mappings = await self._mapping_repo.find_all()
        return [MappingExportDTO.from_mapping(m) for m in mappings]
