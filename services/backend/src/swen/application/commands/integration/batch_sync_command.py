"""Sync transactions across mapped bank accounts (optionally filtered)."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import TYPE_CHECKING, AsyncGenerator, Optional

from swen.application.commands.integration.transaction_sync_command import (
    TransactionSyncCommand,
)
from swen.application.dtos.integration import (
    AccountCompletedEvent,
    AccountFailedEvent,
    AccountStartedEvent,
    BatchSyncResult,
    SyncCompletedEvent,
    SyncProgressEvent,
    SyncResult,
    SyncStartedEvent,
)
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.banking.services import BankBalanceService
from swen.domain.integration.repositories import AccountMappingRepository
from swen.domain.settings.repositories import UserSettingsRepository
from swen.domain.shared.iban import extract_blz_from_iban
from swen.domain.shared.time import today_utc, utc_now
from swen.infrastructure.banking.bank_connection_dispatcher import (
    BankConnectionDispatcher,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.integration.entities import AccountMapping
    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class BatchSyncCommand:
    """Orchestrate multi-account syncs and aggregate results."""

    def __init__(  # NOQA: PLR0913
        self,
        sync_command: TransactionSyncCommand,
        bank_balance_service: BankBalanceService,
        mapping_repo: AccountMappingRepository,
        settings_repo: UserSettingsRepository,
        credential_repo: BankCredentialRepository,
        opening_balance_account_exists: bool,
    ):
        self._sync_command = sync_command
        self._bank_balance_service = bank_balance_service
        self._mapping_repo = mapping_repo
        self._settings_repo = settings_repo
        self._credential_repo = credential_repo
        self._opening_balance_account_exists = opening_balance_account_exists

    @classmethod
    async def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_client: Optional[MLServiceClient] = None,
    ) -> BatchSyncCommand:
        account_repo = factory.account_repository()
        opening_balance_account = await account_repo.find_by_account_number(
            WellKnownAccounts.OPENING_BALANCE_EQUITY,
        )

        bank_adapter = BankConnectionDispatcher.from_factory(factory)
        return cls(
            sync_command=TransactionSyncCommand.from_factory(factory, ml_client),
            bank_balance_service=BankBalanceService(
                bank_adapter=bank_adapter,
                bank_account_repo=factory.bank_account_repository(),
                credential_repo=factory.credential_repository(),
            ),
            mapping_repo=factory.account_mapping_repository(),
            settings_repo=factory.user_settings_repository(),
            credential_repo=factory.credential_repository(),
            opening_balance_account_exists=opening_balance_account is not None,
        )

    async def execute_streaming(
        self,
        days: Optional[int] = None,
        iban: Optional[str] = None,
        blz: Optional[str] = None,
        auto_post: Optional[bool] = None,
    ) -> AsyncGenerator[SyncProgressEvent | BatchSyncResult, None]:
        result, auto_post, start_date, end_date = await self._prepare_sync(
            days,
            auto_post,
        )
        adaptive_mode = days is None

        mappings = await self._get_mappings(iban=iban, blz=blz)

        if not mappings:
            async for event in self._yield_empty_sync_events(result):
                yield event
            return

        yield SyncStartedEvent(total_accounts=len(mappings))

        blzs_needing_refresh: set[str] = set()

        for account_index, mapping in enumerate(mappings, 1):
            async for event in self._sync_single_account_streaming(
                mapping=mapping,
                account_index=account_index,
                total_accounts=len(mappings),
                adaptive_mode=adaptive_mode,
                start_date=start_date,
                end_date=end_date,
                auto_post=auto_post,
                result=result,
            ):
                # If at least one trx was imported we have to refresh balance
                # for reconciliation checks in our bookkeeping system
                if isinstance(event, AccountCompletedEvent) and event.imported > 0:
                    blz = extract_blz_from_iban(mapping.iban)
                    if blz:
                        blzs_needing_refresh.add(blz)
                yield event

        for blz in blzs_needing_refresh:
            if self._bank_balance_service:
                await self._bank_balance_service.refresh_for_blz(blz)

        yield SyncCompletedEvent(
            total_imported=result.total_imported,
            total_skipped=result.total_skipped,
            total_failed=result.total_failed,
            accounts_synced=result.accounts_synced,
        )
        yield result

    async def _prepare_sync(
        self,
        days: Optional[int],
        auto_post: Optional[bool],
    ) -> tuple[BatchSyncResult, bool, date, date]:
        synced_at = utc_now()

        if days is None:
            start_date = end_date = today_utc()
        else:
            start_date, end_date = self._calculate_date_range(days)

        if auto_post is None:
            settings = await self._settings_repo.get_or_create()
            auto_post = settings.sync.auto_post_transactions

        result = BatchSyncResult(
            synced_at=synced_at,
            start_date=start_date,
            end_date=end_date,
            auto_post=auto_post,
            opening_balance_account_missing=not self._opening_balance_account_exists,
        )
        return result, auto_post, start_date, end_date

    async def _yield_empty_sync_events(
        self, result: BatchSyncResult
    ) -> AsyncGenerator[SyncProgressEvent | BatchSyncResult, None]:
        yield SyncStartedEvent(total_accounts=0)
        yield SyncCompletedEvent(
            total_imported=0,
            total_skipped=0,
            total_failed=0,
            accounts_synced=0,
        )
        yield result

    async def _sync_single_account_streaming(  # noqa: PLR0913
        self,
        mapping: AccountMapping,
        account_index: int,
        total_accounts: int,
        adaptive_mode: bool,
        start_date: date,
        end_date: date,
        auto_post: bool,
        result: BatchSyncResult,
    ) -> AsyncGenerator[SyncProgressEvent, None]:
        yield AccountStartedEvent(
            iban=mapping.iban,
            account_name=mapping.account_name,
            account_index=account_index,
            total_accounts=total_accounts,
        )

        try:
            sync_result: Optional[SyncResult] = None
            async for event in self._get_sync_stream(
                mapping.iban,
                adaptive_mode,
                start_date,
                end_date,
                auto_post,
            ):
                if isinstance(event, SyncProgressEvent):
                    yield event
                elif isinstance(event, SyncResult):
                    sync_result = event
                else:
                    logger.warning("Unexpected event from sync stream: %s", type(event))

            if sync_result:
                result.add_result(sync_result)
                self._update_date_range_if_adaptive(result, sync_result, adaptive_mode)

                yield AccountCompletedEvent(
                    iban=mapping.iban,
                    imported=sync_result.transactions_imported,
                    skipped=sync_result.transactions_skipped,
                    failed=sync_result.transactions_failed,
                )
        except Exception as e:
            yield AccountFailedEvent(iban=mapping.iban, error=str(e))
            result.errors.append(f"{mapping.iban}: {e}")

    def _get_sync_stream(
        self,
        iban: str,
        adaptive_mode: bool,  # when start and end date are autocomputed
        start_date: date,
        end_date: date,
        auto_post: bool,
    ) -> AsyncGenerator[SyncProgressEvent | SyncResult, None]:
        if adaptive_mode:
            return self._sync_command.execute_streaming(iban=iban, auto_post=auto_post)
        return self._sync_command.execute_streaming(
            iban=iban,
            start_date=start_date,
            end_date=end_date,
            auto_post=auto_post,
        )

    def _update_date_range_if_adaptive(
        self,
        result: BatchSyncResult,
        sync_result: SyncResult,
        adaptive_mode: bool,
    ) -> None:
        if adaptive_mode and sync_result.start_date and sync_result.end_date:
            result.start_date = min(result.start_date, sync_result.start_date)
            result.end_date = max(result.end_date, sync_result.end_date)

    async def _get_mappings(
        self,
        iban: Optional[str] = None,
        blz: Optional[str] = None,
    ) -> list[AccountMapping]:
        mappings = await self._mapping_repo.find_all()

        if iban:
            mappings = [m for m in mappings if m.iban == iban]
        elif blz:
            mappings = [m for m in mappings if extract_blz_from_iban(m.iban) == blz]

        syncable_mappings = []
        for mapping in mappings:
            mapping_blz = extract_blz_from_iban(mapping.iban)
            if mapping_blz:
                credentials = await self._credential_repo.find_by_blz(mapping_blz)
                if credentials is not None:
                    syncable_mappings.append(mapping)

        return syncable_mappings

    @staticmethod
    def _calculate_date_range(days: int) -> tuple:
        end_date = today_utc()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date
