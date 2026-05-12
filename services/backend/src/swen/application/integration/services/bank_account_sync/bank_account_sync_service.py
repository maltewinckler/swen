"""Per-IBAN sync orchestrator.

Orchestrates the sync pipeline for a single IBAN with pre-resolved
credentials. Replaces the deleted ``TransactionSyncCommand`` minus
credential loading, minus the legacy classify-one-by-one branch, minus
the mixed-payload generator.

See `.kiro/specs/transaction-sync-modularization/design.md` — section
"`BankAccountSyncService` (per-IBAN orchestrator)".
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Optional

from swen.application.integration.services.counter_account_batch_service import (
    CounterAccountBatchService,
)
from swen.application.integration.services.transaction_import_service import (
    TransactionImportService,
)
from swen.domain.accounting.services.opening_balance.service import (
    OpeningBalanceService,
)
from swen.domain.banking.services.bank_balance_service import BankBalanceService
from swen.domain.banking.services.bank_fetch_service import BankFetchService
from swen.domain.integration.exceptions import InactiveMappingError
from swen.domain.integration.services.sync_period_resolver import (
    SyncPeriodResolver,
)

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.integration.services.sync_notification_service import (
        SyncNotificationService,
    )
    from swen.domain.banking.repositories import (
        BankCredentialRepository,
        BankTransactionRepository,
        StoredBankTransaction,
    )
    from swen.domain.banking.value_objects import BankCredentials
    from swen.domain.integration.entities import AccountMapping
    from swen.domain.integration.ports.counter_account_proposal_port import (
        CounterAccountProposalPort,
    )
    from swen.domain.integration.repositories import TransactionImportRepository

logger = logging.getLogger(__name__)


class BankAccountSyncService:
    """Orchestrate sync for a single IBAN with pre-resolved inputs."""

    BATCH_SIZE = 5

    def __init__(  # noqa: PLR0913
        self,
        bank_fetch_service: BankFetchService,
        opening_balance_service: OpeningBalanceService,
        batch_service: CounterAccountBatchService,
        import_service: TransactionImportService,
        bank_balance_service: BankBalanceService,
        bank_transaction_repo: BankTransactionRepository,
        credential_repo: BankCredentialRepository,
        import_repo: TransactionImportRepository,
        notifier: SyncNotificationService,
    ) -> None:
        self._bank_fetch_service = bank_fetch_service
        self._opening_balance_service = opening_balance_service
        self._batch_service = batch_service
        self._import_service = import_service
        self._bank_balance_service = bank_balance_service
        self._bank_transaction_repo = bank_transaction_repo
        self._credential_repo = credential_repo
        self._import_repo = import_repo
        self._notifier = notifier

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        resolution_port: CounterAccountProposalPort,
        notifier: SyncNotificationService,
    ) -> BankAccountSyncService:
        """Build the service and all its dependencies via the factory."""
        opening_balance_service = OpeningBalanceService(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            user_id=factory.current_user.user_id,
        )
        batch_service = CounterAccountBatchService.from_factory(
            factory=factory,
            proposal_port=resolution_port,
        )
        bank_adapter = factory.bank_connection_port()
        bank_fetch_service = BankFetchService(bank_adapter=bank_adapter)
        return cls(
            bank_fetch_service=bank_fetch_service,
            opening_balance_service=opening_balance_service,
            batch_service=batch_service,
            import_service=TransactionImportService.from_factory(factory),
            bank_balance_service=BankBalanceService(
                bank_fetch_service=bank_fetch_service,
                bank_account_repo=factory.bank_account_repository(),
                credential_repo=factory.credential_repository(),
            ),
            bank_transaction_repo=factory.bank_transaction_repository(),
            credential_repo=factory.credential_repository(),
            import_repo=factory.import_repository(),
            notifier=notifier,
        )

    async def sync_account(
        self,
        mapping: AccountMapping,
        days: Optional[int],  # when given overrides adaptive logic (not yet productive)
        auto_post: bool,  # injected from upstream command, based on user setting
    ) -> tuple[int, int, int]:
        """Orchestrate sync for a single IBAN."""
        iban = mapping.iban
        blz = mapping.blz
        if not mapping.is_active:
            msg = f"Account mapping for {iban} is inactive"
            raise InactiveMappingError(msg)

        credentials = await self._credential_repo.find_by_blz(blz)
        tan_method, tan_medium = await self._credential_repo.get_tan_settings(blz)
        if credentials is None:
            logger.warning("Credentials missing for BLZ %s (account %s)", blz, iban)
            return 0, 0, 0

        to_import = await self._fetch_and_store(
            iban=iban,
            days=days,
            credentials=credentials,
            tan_method=tan_method,
            tan_medium=tan_medium,
        )
        await self._compute_opening_balance(
            iban=iban, stored_bank_transactions=to_import
        )

        await self._credential_repo.update_last_used(blz)

        imported, skipped, failed = await self._process_batch_loop(
            to_import=to_import,
            iban=iban,
            auto_post=auto_post,
        )

        if imported > 0:
            await self._bank_balance_service.refresh_for_blz(blz)
        return imported, skipped, failed

    async def _fetch_and_store(
        self,
        iban: str,
        days: Optional[int],
        credentials: BankCredentials,
        tan_method: Optional[str],
        tan_medium: Optional[str],
    ) -> list[StoredBankTransaction]:
        """Resolve period, fetch from bank and store with dedup."""
        latest = await self._import_repo.find_latest_booking_date_by_iban(iban)
        period = SyncPeriodResolver.resolve_period(latest=latest, days=days)

        bank_transactions = await self._bank_fetch_service.fetch_transactions(
            credentials=credentials,
            iban=iban,
            start_date=period.start_date,
            end_date=period.end_date,
            tan_method=tan_method,
            tan_medium=tan_medium,
        )
        stored_transactions = (
            await self._bank_transaction_repo.save_batch_with_deduplication(
                transactions=bank_transactions,
                account_iban=iban,
            )
        )
        to_import = [s for s in stored_transactions if s.is_new or not s.is_imported]

        await self._notifier.emit_account_sync_fetched_event(
            transactions_fetched=len(bank_transactions),
            new_transactions=len(to_import),
        )
        if not to_import:
            d = len(bank_transactions)
            logger.info("All %d transactions already imported for %s", d, iban)
        return to_import

    async def _compute_opening_balance(
        self,
        iban: str,
        stored_bank_transactions: list[StoredBankTransaction],
    ):
        """Get current balance and attempt opening-balance creation for a first sync."""
        current_balance = await self._bank_balance_service.get_for_iban(iban)
        if current_balance is not None:
            await self._opening_balance_service.try_create_for_first_sync(
                iban=iban,
                current_balance=current_balance,
                bank_transactions=[s.transaction for s in stored_bank_transactions],
            )

    async def _process_batch_loop(
        self,
        to_import: list[StoredBankTransaction],
        iban: str,
        auto_post: bool,
    ) -> tuple[int, int, int]:
        """Classify and import in interleaved batches, publishing SSE events."""
        total = len(to_import)
        if total == 0:
            return 0, 0, 0

        await self._notifier.emit_classification_started_event()

        start_ms = time.monotonic()

        for batch_start in range(0, total, self.BATCH_SIZE):
            batch = to_import[batch_start : batch_start + self.BATCH_SIZE]

            resolved = await self._batch_service.resolve_batch(batch)

            await self._notifier.emit_classification_progress_event(
                current=min(batch_start + len(batch), total),
                total=total,
            )

            batch_results = await self._import_service.import_batch(
                stored_transactions=batch,
                source_iban=iban,
                resolved=resolved,
                auto_post=auto_post,
            )
            imported, skipped, failed = self._import_service.compute_stats(
                batch_results
            )

        elapsed_ms = int((time.monotonic() - start_ms) * 1000)
        await self._notifier.emit_classification_completed_event(
            total=total,
            processing_time_ms=elapsed_ms,
        )

        return imported, skipped, failed
