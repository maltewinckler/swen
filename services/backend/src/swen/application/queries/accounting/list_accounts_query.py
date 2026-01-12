"""List accounts query - retrieve accounts for display."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from swen.application.dtos.accounting import (
    AccountSummaryDTO,
    BankAccountDTO,
    ChartOfAccountsDTO,
)
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.repositories import AccountRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
from swen.domain.integration.repositories import AccountMappingRepository


@dataclass
class AccountListResult:
    """Result of listing accounts."""

    accounts: list[AccountSummaryDTO]
    total_count: int
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
    ) -> AccountListResult:
        accounts = await self._fetch_accounts(account_type, active_only)

        by_type: dict[str, int] = {}
        account_dtos: list[AccountSummaryDTO] = []

        for acc in accounts:
            type_name = acc.account_type.value.upper()
            by_type[type_name] = by_type.get(type_name, 0) + 1
            account_dtos.append(AccountSummaryDTO.from_entity(acc))

        return AccountListResult(
            accounts=account_dtos,
            total_count=len(account_dtos),
            by_type=by_type,
        )

    async def get_chart_of_accounts(
        self,
        account_type: Optional[str] = None,
        active_only: bool = True,
    ) -> ChartOfAccountsDTO:
        accounts = await self._fetch_accounts(account_type, active_only)

        by_type: dict[AccountType, list[Account]] = {
            AccountType.ASSET: [],
            AccountType.LIABILITY: [],
            AccountType.EQUITY: [],
            AccountType.INCOME: [],
            AccountType.EXPENSE: [],
        }

        for acc in accounts:
            by_type[acc.account_type].append(acc)

        def to_sorted_dtos(
            account_list: list[Account],
        ) -> tuple[AccountSummaryDTO, ...]:
            sorted_accounts = sorted(account_list, key=lambda a: a.account_number or "")
            return tuple(AccountSummaryDTO.from_entity(acc) for acc in sorted_accounts)

        return ChartOfAccountsDTO(
            assets=to_sorted_dtos(by_type[AccountType.ASSET]),
            liabilities=to_sorted_dtos(by_type[AccountType.LIABILITY]),
            equity=to_sorted_dtos(by_type[AccountType.EQUITY]),
            income=to_sorted_dtos(by_type[AccountType.INCOME]),
            expenses=to_sorted_dtos(by_type[AccountType.EXPENSE]),
        )

    async def find_by_id(self, account_id: UUID) -> Optional[AccountSummaryDTO]:
        account = await self._account_repo.find_by_id(account_id)
        if account is None:
            return None
        return AccountSummaryDTO.from_entity(account)

    async def find_by_account_number(
        self,
        account_number: str,
    ) -> Optional[AccountSummaryDTO]:
        account = await self._account_repo.find_by_account_number(account_number)
        if account is None:
            return None
        return AccountSummaryDTO.from_entity(account)

    async def find_by_name(self, name: str) -> Optional[AccountSummaryDTO]:
        account = await self._account_repo.find_by_name(name)
        if account is None:
            return None
        return AccountSummaryDTO.from_entity(account)

    async def find_by_type(self, account_type: str) -> list[AccountSummaryDTO]:
        accounts = await self._account_repo.find_by_type(account_type.lower())
        return [AccountSummaryDTO.from_entity(acc) for acc in accounts]

    async def list_bank_accounts(self) -> list[BankAccountDTO]:
        if not self._mapping_repo:
            return []

        mappings = await self._mapping_repo.find_all()
        results: list[BankAccountDTO] = []

        for mapping in mappings:
            account = await self._account_repo.find_by_id(mapping.accounting_account_id)
            if account:
                results.append(BankAccountDTO.from_entities(account, mapping))

        return results

    async def account_number_exists(self, account_number: str) -> bool:
        existing = await self._account_repo.find_by_account_number(account_number)
        return existing is not None

    async def account_name_exists(self, name: str) -> bool:
        existing = await self._account_repo.find_by_name(name)
        return existing is not None

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
