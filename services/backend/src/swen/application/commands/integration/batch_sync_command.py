"""Sync transactions across mapped bank accounts (optionally filtered)."""

from __future__ import annotations

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
    SyncStartedEvent,
)
from swen.application.queries import GetCurrentUserQuery, ListAccountMappingsQuery
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.shared.iban import extract_blz_from_iban
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


# Required account for opening balance creation
OPENING_BALANCE_ACCOUNT_NUMBER = "2000"


class BatchSyncCommand:
    """Orchestrate multi-account syncs and aggregate results."""

    def __init__(  # NOQA: PLR0913
        self,
        sync_command: TransactionSyncCommand,
        user_query: GetCurrentUserQuery,
        mapping_query: ListAccountMappingsQuery,
        credential_repo: BankCredentialRepository,
        email: str,
        opening_balance_account_exists: bool,
    ):
        self._sync_command = sync_command
        self._user_query = user_query
        self._mapping_query = mapping_query
        self._credential_repo = credential_repo
        self._email = email
        self._opening_balance_account_exists = opening_balance_account_exists

    @classmethod
    async def from_factory(cls, factory: RepositoryFactory) -> BatchSyncCommand:
        account_repo = factory.account_repository()
        opening_balance_account = await account_repo.find_by_account_number(
            OPENING_BALANCE_ACCOUNT_NUMBER,
        )

        return cls(
            sync_command=TransactionSyncCommand.from_factory(factory),
            user_query=GetCurrentUserQuery.from_factory(factory),
            mapping_query=ListAccountMappingsQuery.from_factory(factory),
            credential_repo=factory.credential_repository(),
            email=factory.user_context.email,
            opening_balance_account_exists=opening_balance_account is not None,
        )

    async def execute(
        self,
        days: Optional[int] = None,
        iban: Optional[str] = None,
        blz: Optional[str] = None,
        auto_post: Optional[bool] = None,
    ) -> BatchSyncResult:
        synced_at = utc_now()
        adaptive_mode = days is None

        # Calculate date range for fixed mode, or use placeholders for adaptive
        if adaptive_mode:
            # In adaptive mode, actual dates are determined per-account
            # Use today as placeholder for the result DTO
            start_date = date.today()
            end_date = date.today()
        else:
            start_date, end_date = self._calculate_date_range(days)

        # Determine auto_post from user preference if not overridden
        if auto_post is None:
            user = await self._user_query.execute(self._email)
            auto_post = user.preferences.sync_settings.auto_post_transactions

        # Create result DTO
        result = BatchSyncResult(
            synced_at=synced_at,
            start_date=start_date,
            end_date=end_date,
            auto_post=auto_post,
            opening_balance_account_missing=not self._opening_balance_account_exists,
        )

        # Get account mappings
        mappings = await self._get_mappings(iban=iban, blz=blz)
        if not mappings:
            return result

        # Sync each account
        for mapping in mappings:
            if adaptive_mode:
                # Let TransactionSyncCommand determine dates from import history
                sync_result = await self._sync_command.execute(
                    iban=mapping.iban,
                    # No start_date/end_date - adaptive mode
                    auto_post=auto_post,
                )
            else:
                # Use fixed date range
                sync_result = await self._sync_command.execute(
                    iban=mapping.iban,
                    start_date=start_date,
                    end_date=end_date,
                    auto_post=auto_post,
                )
            result.add_result(sync_result)

            # Update result's date range based on actual sync dates
            if adaptive_mode and sync_result.start_date and sync_result.end_date:
                # Track the actual date range that was synced
                result.start_date = min(result.start_date, sync_result.start_date)
                result.end_date = max(result.end_date, sync_result.end_date)

        return result

    async def execute_streaming(
        self,
        days: Optional[int] = None,
        iban: Optional[str] = None,
        blz: Optional[str] = None,
        auto_post: Optional[bool] = None,
    ) -> AsyncGenerator[
        SyncProgressEvent
        | AccountStartedEvent
        | AccountCompletedEvent
        | AccountFailedEvent
        | BatchSyncResult,
        None,
    ]:
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
                yield event

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
            start_date = end_date = date.today()
        else:
            start_date, end_date = self._calculate_date_range(days)

        if auto_post is None:
            user = await self._user_query.execute(self._email)
            auto_post = user.preferences.sync_settings.auto_post_transactions

        result = BatchSyncResult(
            synced_at=synced_at,
            start_date=start_date,
            end_date=end_date,
            auto_post=auto_post,
            opening_balance_account_missing=not self._opening_balance_account_exists,
        )
        return result, auto_post, start_date, end_date

    async def _yield_empty_sync_events(self, result: BatchSyncResult):
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
        mapping,
        account_index: int,
        total_accounts: int,
        adaptive_mode: bool,
        start_date: date,
        end_date: date,
        auto_post: bool,
        result: BatchSyncResult,
    ) -> AsyncGenerator:
        yield AccountStartedEvent(
            iban=mapping.iban,
            account_name=mapping.account_name,
            account_index=account_index,
            total_accounts=total_accounts,
        )

        try:
            sync_result = None
            async for event in self._get_sync_stream(
                mapping.iban,
                adaptive_mode,
                start_date,
                end_date,
                auto_post,
            ):
                if isinstance(event, SyncProgressEvent):
                    yield event
                else:
                    sync_result = event

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
        adaptive_mode: bool,
        start_date: date,
        end_date: date,
        auto_post: bool,
    ):
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
        sync_result,
        adaptive_mode: bool,
    ) -> None:
        if adaptive_mode and sync_result.start_date and sync_result.end_date:
            result.start_date = min(result.start_date, sync_result.start_date)
            result.end_date = max(result.end_date, sync_result.end_date)

    async def _get_mappings(
        self,
        iban: Optional[str] = None,
        blz: Optional[str] = None,
    ) -> list:
        mapping_result = await self._mapping_query.execute()
        mappings = mapping_result.mappings

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
    def _calculate_date_range(days: int) -> tuple[date, date]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        return start_date, end_date
