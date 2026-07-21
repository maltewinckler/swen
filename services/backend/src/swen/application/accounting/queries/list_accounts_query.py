"""List accounts query - retrieve accounts for display."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from swen.application.accounting.dtos import (
    AccountSummaryDTO,
    BankAccountDTO,
)
from swen.domain.accounting.entities import Account
from swen.domain.accounting.repositories import AccountRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
from swen.domain.integration.repositories import AccountMappingRepository


class AccountListDTO(BaseModel):
    """Result of listing accounts."""

    model_config = ConfigDict(frozen=True)

    accounts: list[AccountSummaryDTO]
    total: int
    by_type: dict[str, int]


class ListAccountsQuery:
    """Query to list accounts with filters."""

    def __init__(
        self,
        account_repository: AccountRepository,
        mapping_repository: Optional[AccountMappingRepository] = None,
    ):
        self._account_repo = account_repository
        self._mapping_repo = mapping_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ListAccountsQuery:
        return cls(
            account_repository=factory.account_repository(),
            mapping_repository=factory.account_mapping_repository(),
        )

    async def execute(
        self,
        account_type: Optional[str] = None,
        active_only: bool = True,
    ) -> AccountListDTO:
        accounts = await self._fetch_accounts(account_type, active_only)

        by_type: dict[str, int] = {}
        account_dtos: list[AccountSummaryDTO] = []

        for acc in accounts:
            type_name = acc.account_type.value.upper()
            by_type[type_name] = by_type.get(type_name, 0) + 1
            account_dtos.append(AccountSummaryDTO.from_entity(acc))

        return AccountListDTO(
            accounts=account_dtos,
            total=len(account_dtos),
            by_type=by_type,
        )

    async def find_by_id(self, account_id: UUID) -> Optional[AccountSummaryDTO]:
        # actually used
        account = await self._account_repo.find_by_id(account_id)
        if account is None:
            return None
        return AccountSummaryDTO.from_entity(account)

    async def list_bank_accounts(self) -> list[BankAccountDTO]:
        # actually used
        if not self._mapping_repo:
            return []

        mappings = await self._mapping_repo.find_all()
        results: list[BankAccountDTO] = []

        for mapping in mappings:
            account = await self._account_repo.find_by_id(mapping.accounting_account_id)
            if account:
                results.append(BankAccountDTO.from_entities(account, mapping))

        return results

    async def _fetch_accounts(
        self,
        account_type: Optional[str],
        active_only: bool,
    ) -> list[Account]:
        if account_type:
            return await self._account_repo.find_by_type(account_type.lower())
        if active_only:
            return await self._account_repo.find_all_active()
        return await self._account_repo.find_all()
