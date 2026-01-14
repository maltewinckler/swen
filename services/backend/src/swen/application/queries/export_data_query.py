"""Export data query - retrieve data for export.

This query encapsulates the logic for fetching data to export,
keeping the CLI layer focused on presentation only.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Optional

from swen.application.dtos.export_dto import (
    AccountExportDTO,
    ExportResult,
    MappingExportDTO,
    TransactionExportDTO,
)
from swen.domain.accounting.repositories import AccountRepository, TransactionRepository
from swen.domain.integration.repositories import AccountMappingRepository
from swen.domain.settings.repositories import UserSettingsRepository
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class ExportDataQuery:
    """Query to fetch data for export."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
        account_repository: AccountRepository,
        mapping_repository: Optional[AccountMappingRepository] = None,
        settings_repository: Optional[UserSettingsRepository] = None,
    ):
        self._transaction_repo = transaction_repository
        self._account_repo = account_repository
        self._mapping_repo = mapping_repository
        self._settings_repo = settings_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ExportDataQuery:
        return cls(
            transaction_repository=factory.transaction_repository(),
            account_repository=factory.account_repository(),
            mapping_repository=factory.account_mapping_repository(),
            settings_repository=factory.user_settings_repository(),
        )

    async def _get_include_drafts_from_preference(self) -> bool:
        if self._settings_repo:
            settings = await self._settings_repo.get_or_create()
            return settings.display.show_draft_transactions
        return True  # Default to including drafts

    async def execute(
        self,
        days: int = 0,
        status: Optional[str] = None,
    ) -> ExportResult:
        transactions = await self.get_transactions(days=days, status=status)
        all_accounts = await self._account_repo.find_all()

        return ExportResult(
            transactions=transactions,
            accounts=[AccountExportDTO.from_account(a) for a in all_accounts],
        )

    async def execute_full_export(self, days: int = 0) -> ExportResult:
        transactions = await self.get_transactions(days=days, status="all")
        accounts = await self.get_accounts(include_inactive=True)

        # Get mappings
        mappings: list[MappingExportDTO] = []
        if self._mapping_repo:
            all_mappings = await self._mapping_repo.find_all()
            mappings = [MappingExportDTO.from_mapping(m) for m in all_mappings]

        return ExportResult(
            transactions=transactions,
            accounts=accounts,
            mappings=mappings,
        )

    async def get_transactions(
        self,
        days: int = 0,
        status: Optional[str] = None,
        iban: Optional[str] = None,
    ) -> list[TransactionExportDTO]:
        effective_status = status
        if status is None:
            include_drafts = await self._get_include_drafts_from_preference()
            if not include_drafts:
                effective_status = "posted"
        elif status == "all":
            effective_status = None

        start_date = None
        if days > 0:
            now = utc_now()
            start_date = (now - timedelta(days=days)).isoformat()

        account_id = None
        if iban and self._mapping_repo:
            mapping = await self._mapping_repo.find_by_iban(iban)
            if mapping:
                account_id = mapping.accounting_account_id
            else:
                return []

        all_transactions = await self._transaction_repo.find_with_filters(
            start_date=start_date,
            status=effective_status,
            account_id=account_id,
        )

        return [TransactionExportDTO.from_transaction(t) for t in all_transactions]

    async def get_accounts(
        self,
        account_type: Optional[str] = None,
        include_inactive: bool = False,
    ) -> list[AccountExportDTO]:
        all_accounts = await self._account_repo.find_all()
        accounts = [AccountExportDTO.from_account(a) for a in all_accounts]

        if account_type:
            accounts = [a for a in accounts if a.type == account_type.lower()]
        if not include_inactive:
            accounts = [a for a in accounts if a.is_active]

        return accounts
