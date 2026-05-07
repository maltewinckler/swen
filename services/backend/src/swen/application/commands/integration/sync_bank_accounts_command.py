"""Sync transactions across mapped bank accounts (single use-case Command).

Replaces ``BatchSyncCommand``. Resolves syncable mappings, prepares the date
range and ``auto_post``, fans out to ``BankAccountSyncService``, refreshes
per-BLZ balances after writes, and assembles ``BatchSyncResult`` from
per-account ``SyncResult``s.

See `.kiro/specs/transaction-sync-modularization/design.md` — section
"`SyncBankAccountsCommand` (replaces `BatchSyncCommand`)".
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from swen.application.dtos.integration import (
    AccountSyncCompletedEvent,
    AccountSyncFailedEvent,
    BatchSyncCompletedEvent,
    BatchSyncResult,
    BatchSyncResultBuilder,
    BatchSyncStartedEvent,
    ErrorCode,
    SyncPeriod,
)
from swen.application.services.integration.bank_account_sync_service import (
    BankAccountSyncService,
)
from swen.application.services.integration.sync_period_resolver import (
    SyncPeriodResolver,
)
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.accounting.well_known_accounts import WellKnownAccounts
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.banking.services import BankBalanceService
from swen.domain.integration.repositories import AccountMappingRepository
from swen.domain.settings.repositories import UserSettingsRepository
from swen.domain.shared.iban import extract_blz_from_iban
from swen.domain.shared.time import today_utc, utc_now

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.integration.sync_event_publisher import (
        SyncEventPublisher,
    )
    from swen.domain.integration.entities import AccountMapping
    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class SyncBankAccountsCommand:
    """Orchestrate multi-account syncs and aggregate results."""

    def __init__(  # noqa: PLR0913
        self,
        sync_service: BankAccountSyncService,
        bank_balance_service: BankBalanceService,
        period_resolver: SyncPeriodResolver,
        mapping_repo: AccountMappingRepository,
        settings_repo: UserSettingsRepository,
        credential_repo: BankCredentialRepository,
        account_repo: AccountRepository,
        publisher: SyncEventPublisher,
    ) -> None:
        self._sync_service = sync_service
        self._bank_balance_service = bank_balance_service
        self._period_resolver = period_resolver
        self._mapping_repo = mapping_repo
        self._settings_repo = settings_repo
        self._credential_repo = credential_repo
        self._account_repo = account_repo
        self._publisher = publisher

    @classmethod
    async def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_client: MLServiceClient,
        publisher: SyncEventPublisher,
    ) -> SyncBankAccountsCommand:
        """Build the command and all its dependencies via the factory."""
        sync_service = BankAccountSyncService.from_factory(
            factory, ml_client, publisher
        )

        bank_adapter = factory.bank_connection_port()
        bank_balance_service = BankBalanceService(
            bank_adapter=bank_adapter,
            bank_account_repo=factory.bank_account_repository(),
            credential_repo=factory.credential_repository(),
        )

        period_resolver = SyncPeriodResolver.from_factory(factory)

        return cls(
            sync_service=sync_service,
            bank_balance_service=bank_balance_service,
            period_resolver=period_resolver,
            mapping_repo=factory.account_mapping_repository(),
            settings_repo=factory.user_settings_repository(),
            credential_repo=factory.credential_repository(),
            account_repo=factory.account_repository(),
            publisher=publisher,
        )

    async def execute(
        self,
        days: Optional[int] = None,
        iban: Optional[str] = None,
        blz: Optional[str] = None,
        auto_post: Optional[bool] = None,
    ) -> BatchSyncResult:
        """Run the batch sync across all matching account mappings."""
        # --- Per-run lookups and config preparation (task 5.2) ---

        # Look up opening-balance equity account per run (NOT in constructor)
        opening_balance_account = await self._account_repo.find_by_account_number(
            WellKnownAccounts.OPENING_BALANCE_EQUITY,
        )
        opening_balance_account_missing = opening_balance_account is None

        # Resolve mapping list
        syncable = await self._get_mappings(iban=iban, blz=blz)

        # Resolve auto_post from UserSettingsRepository when None
        if auto_post is None:
            settings = await self._settings_repo.get_or_create()
            auto_post = settings.sync.auto_post_transactions

        # Compute period
        if days is not None:
            period = self._period_resolver.resolve_fixed(days)
        else:
            # Adaptive placeholder — per-IBAN service will resolve per account
            period = SyncPeriod(
                start_date=today_utc(), end_date=today_utc(), adaptive=True
            )

        synced_at = utc_now()
        builder = BatchSyncResultBuilder(
            synced_at=synced_at,
            start_date=period.start_date,
            end_date=period.end_date,
            auto_post=auto_post,
            opening_balance_account_missing=opening_balance_account_missing,
        )

        # --- Empty-mappings edge case (task 5.5) ---
        if not syncable:
            await self._publisher.publish(BatchSyncStartedEvent(total_accounts=0))
            result = builder.build()
            await self._publisher.publish(
                BatchSyncCompletedEvent(
                    total_imported=0,
                    total_skipped=0,
                    total_failed=0,
                    accounts_synced=0,
                )
            )
            await self._publisher.publish_terminal(result)
            return result

        # --- Per-account loop and event publishing (task 5.3) ---
        await self._publisher.publish(
            BatchSyncStartedEvent(total_accounts=len(syncable))
        )

        blzs_needing_refresh: set[str] = set()

        for account_index, mapping in enumerate(syncable, 1):
            mapping_blz = extract_blz_from_iban(mapping.iban)

            try:
                # Load credentials once per mapping
                credentials = await self._credential_repo.find_by_blz(mapping_blz)  # type: ignore[arg-type]
                if credentials is None:
                    msg = f"No credentials found for BLZ {mapping_blz}"
                    raise RuntimeError(msg)

                sync_result = await self._sync_service.sync_account(
                    mapping=mapping,
                    credentials=credentials,
                    period=period,
                    auto_post=auto_post,
                    account_index=account_index,
                    total_accounts=len(syncable),
                )

                # Add to builder
                builder.add_account(sync_result)

                # Widen period when adaptive
                if period.adaptive and sync_result.start_date and sync_result.end_date:
                    builder.widen_period(sync_result.start_date, sync_result.end_date)

                # Publish AccountSyncCompleted
                await self._publisher.publish(
                    AccountSyncCompletedEvent(
                        iban=mapping.iban,
                        imported=sync_result.transactions_imported,
                        skipped=sync_result.transactions_skipped,
                        failed=sync_result.transactions_failed,
                    )
                )

                # Track BLZ when imported > 0
                if sync_result.transactions_imported > 0 and mapping_blz:
                    blzs_needing_refresh.add(mapping_blz)

            except Exception as e:
                logger.exception("Sync failed for account %s: %s", mapping.iban, e)
                await self._publisher.publish(
                    AccountSyncFailedEvent(
                        iban=mapping.iban,
                        code=ErrorCode.INTERNAL_ERROR,
                        error_key=str(e),
                    )
                )
                builder.add_error(mapping.iban, str(e))

        # --- Post-loop balance refresh and terminal payload (task 5.4) ---
        for blz_to_refresh in blzs_needing_refresh:
            await self._bank_balance_service.refresh_for_blz(blz_to_refresh)

        result = builder.build()

        await self._publisher.publish(
            BatchSyncCompletedEvent(
                total_imported=result.total_imported,
                total_skipped=result.total_skipped,
                total_failed=result.total_failed,
                accounts_synced=result.accounts_synced,
            )
        )
        await self._publisher.publish_terminal(result)

        return result

    async def _get_mappings(
        self,
        iban: Optional[str] = None,
        blz: Optional[str] = None,
    ) -> list[AccountMapping]:
        """Resolve syncable mappings with iban precedence over blz filtering.

        Excludes mappings whose BLZ has no stored credentials.
        """
        mappings = await self._mapping_repo.find_all()

        if iban:
            mappings = [m for m in mappings if m.iban == iban]
        elif blz:
            mappings = [m for m in mappings if extract_blz_from_iban(m.iban) == blz]

        syncable_mappings: list[AccountMapping] = []
        for mapping in mappings:
            mapping_blz = extract_blz_from_iban(mapping.iban)
            if mapping_blz:
                credentials = await self._credential_repo.find_by_blz(mapping_blz)
                if credentials is not None:
                    syncable_mappings.append(mapping)

        return syncable_mappings
