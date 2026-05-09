"""Sync transactions across mapped bank accounts (single use-case Command).

Replaces ``BatchSyncCommand``. Resolves syncable mappings, prepares the date
range and ``auto_post``, fans out to ``BankAccountSyncService``, refreshes
per-BLZ balances after writes, and publishes a terminal ``SyncResultEvent``
with aggregated counts.

See `.kiro/specs/transaction-sync-modularization/design.md` — section
"`SyncBankAccountsCommand` (replaces `BatchSyncCommand`)".
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from swen.application.events import ErrorCode
from swen.application.services.integration.bank_account_sync import (
    BankAccountSyncService,
)
from swen.application.services.integration.sync_notification_service import (
    SyncNotificationService,
)
from swen.domain.banking.repositories import BankCredentialRepository
from swen.domain.integration.repositories import AccountMappingRepository
from swen.domain.settings.repositories import UserSettingsRepository

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.integration.sync_event_publisher import (
        SyncEventPublisher,
    )
    from swen.domain.integration.entities import AccountMapping
    from swen.domain.integration.ports.counter_account_proposal_port import (
        CounterAccountProposalPort,
    )

logger = logging.getLogger(__name__)


class SyncBankAccountsCommand:
    """Orchestrate multi-account syncs and aggregate results."""

    def __init__(
        self,
        sync_service: BankAccountSyncService,
        mapping_repo: AccountMappingRepository,
        settings_repo: UserSettingsRepository,
        credential_repo: BankCredentialRepository,
        notifier: SyncNotificationService,
    ) -> None:
        self._sync_service = sync_service
        self._mapping_repo = mapping_repo
        self._settings_repo = settings_repo
        self._credential_repo = credential_repo
        self._notifier = notifier

    @classmethod
    async def from_factory(
        cls,
        factory: RepositoryFactory,
        resolution_port: CounterAccountProposalPort,
        publisher: SyncEventPublisher,
    ) -> SyncBankAccountsCommand:
        notifier = SyncNotificationService(publisher)

        sync_service = BankAccountSyncService.from_factory(
            factory, resolution_port, notifier
        )
        return cls(
            sync_service=sync_service,
            mapping_repo=factory.account_mapping_repository(),
            settings_repo=factory.user_settings_repository(),
            credential_repo=factory.credential_repository(),
            notifier=notifier,
        )

    async def execute(
        self,
        days: Optional[int] = None,
        blz: Optional[str] = None,
    ):
        """Run the batch sync across all matching account mappings."""
        mappings = await self._get_account_mappings(blz)
        auto_post = await self._resolve_auto_post()

        if not mappings:
            await self._notifier.emit_batch_sync_started_event(0)
            await self._notifier.emit_batch_sync_completed_event()
            await self._notifier.emit_sync_result_event()
            await self._notifier.close()
            return

        await self._notifier.emit_batch_sync_started_event(len(mappings))

        for mapping in mappings:
            try:
                await self._notifier.emit_account_sync_started_event(
                    iban=mapping.iban,
                    account_name=mapping.account_name,
                )

                imported, skipped, failed = await self._sync_service.sync_account(
                    mapping=mapping,
                    days=days,
                    auto_post=auto_post,
                )
                await self._notifier.emit_account_sync_completed_event(
                    imported, skipped, failed
                )

            except Exception as e:
                logger.exception("Sync failed for account %s: %s", mapping.iban, e)
                await self._notifier.emit_account_sync_failed_event(
                    code=ErrorCode.INTERNAL_ERROR,
                    error_key=str(e),
                )

        await self._notifier.emit_batch_sync_completed_event()
        await self._notifier.emit_sync_result_event()
        await self._notifier.close()

    async def _resolve_auto_post(self) -> bool:
        settings = await self._settings_repo.get_or_create()
        return settings.sync.auto_post_transactions

    async def _get_account_mappings(self, blz: Optional[str]) -> list[AccountMapping]:
        mappings = await self._mapping_repo.find_all()
        if blz:
            mappings = [m for m in mappings if m.blz == blz]
        return mappings
