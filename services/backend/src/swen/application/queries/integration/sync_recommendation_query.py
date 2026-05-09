"""Sync recommendation query - determine adaptive sync parameters."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from swen.application.dtos.integration import (
    AccountSyncRecommendationDTO,
    SyncRecommendationResultDTO,
)
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.integration.repositories import (
    AccountMappingRepository,
    TransactionImportRepository,
)
from swen.domain.shared.iban import extract_blz_from_iban

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


# Buffer days to extend the sync window for safety
SYNC_BUFFER_DAYS = 2


class SyncRecommendationQuery:
    """Query to get sync recommendations for adaptive synchronization.

    This query helps the frontend implement adaptive sync:
    1. First sync: Ask user how many days of history to load
    2. Subsequent syncs: Automatically sync from last sync date
    """

    def __init__(
        self,
        mapping_repo: AccountMappingRepository,
        import_repo: TransactionImportRepository,
        credential_repo: BankCredentialRepository,
    ):
        self._mapping_repo = mapping_repo
        self._import_repo = import_repo
        self._credential_repo = credential_repo

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> SyncRecommendationQuery:
        return cls(
            mapping_repo=factory.account_mapping_repository(),
            import_repo=factory.import_repository(),
            credential_repo=factory.credential_repository(),
        )

    async def execute(self) -> SyncRecommendationResultDTO:
        mappings = await self._mapping_repo.find_all()
        active_mappings = [m for m in mappings if m.is_active]

        syncable_mappings = []
        for mapping in active_mappings:
            blz = extract_blz_from_iban(mapping.iban)
            if blz:
                credentials = await self._credential_repo.find_by_blz(blz)
                if credentials is not None:
                    syncable_mappings.append(mapping)

        recommendations = []
        has_first_sync = False

        for mapping in syncable_mappings:
            rec = await self._get_recommendation_for_iban(mapping.iban)
            recommendations.append(rec)
            if rec.is_first_sync:
                has_first_sync = True

        return SyncRecommendationResultDTO(
            accounts=tuple(recommendations),
            has_first_sync_accounts=has_first_sync,
            total_accounts=len(recommendations),
        )

    async def _get_recommendation_for_iban(
        self,
        iban: str,
    ) -> AccountSyncRecommendationDTO:
        last_booking_date = await self._import_repo.find_latest_booking_date_by_iban(
            iban
        )

        if last_booking_date is None:
            return AccountSyncRecommendationDTO(
                iban=iban,
                is_first_sync=True,
                recommended_start_date=None,
                last_successful_sync_date=None,
                successful_import_count=0,
            )

        recommended_start = last_booking_date - timedelta(days=SYNC_BUFFER_DAYS)

        return AccountSyncRecommendationDTO(
            iban=iban,
            is_first_sync=False,
            recommended_start_date=recommended_start,
            last_successful_sync_date=last_booking_date,
            successful_import_count=1,
        )
