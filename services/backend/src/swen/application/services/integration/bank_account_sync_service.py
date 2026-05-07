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
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from swen.application.dtos.integration.sync_progress import (
    AccountSyncFetchedEvent,
    AccountSyncStartedEvent,
    ClassificationCompletedEvent,
    ClassificationProgressEvent,
    ClassificationStartedEvent,
    TransactionClassifiedEvent,
)
from swen.application.services.integration.bank_fetch_service import (
    BankFetchService,
    TanCallback,
)
from swen.application.services.integration.current_balance_service import (
    CurrentBalanceService,
)
from swen.application.services.integration.exceptions import InactiveMappingError
from swen.application.services.integration.sync_period_resolver import (
    SyncPeriodResolver,
)
from swen.application.services.integration.sync_result_aggregator import (
    SyncResultAggregator,
)
from swen.application.services.ml_batch_classification_service import (
    MLBatchClassificationService,
)
from swen.application.services.transaction_import_service import (
    TransactionImportService,
)
from swen.domain.accounting.services.opening_balance.service import (
    OpeningBalanceOutcome,
    OpeningBalanceService,
)
from swen.domain.shared.iban import extract_blz_from_iban
from swen.domain.shared.time import utc_now

if TYPE_CHECKING:
    from swen.application.dtos.integration.sync_period import SyncPeriod
    from swen.application.dtos.integration.sync_result import SyncResult
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.integration.sync_event_publisher import (
        SyncEventPublisher,
    )
    from swen.application.services.ml_batch_classification_service import (
        BatchClassificationResult,
    )
    from swen.domain.banking.repositories import (
        BankCredentialRepository,
        BankTransactionRepository,
    )
    from swen.domain.banking.value_objects import BankCredentials
    from swen.domain.integration.entities import AccountMapping
    from swen.domain.integration.repositories import TransactionImportRepository
    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class BankAccountSyncService:
    """Orchestrate sync for a single IBAN with pre-resolved inputs."""

    def __init__(  # noqa: PLR0913
        self,
        bank_fetch_service: BankFetchService,
        opening_balance_service: OpeningBalanceService,
        ml_classification_service: MLBatchClassificationService,
        import_service: TransactionImportService,
        result_aggregator: SyncResultAggregator,
        period_resolver: SyncPeriodResolver,
        current_balance_service: CurrentBalanceService,
        bank_transaction_repo: BankTransactionRepository,
        import_repo: TransactionImportRepository,
        credential_repo: BankCredentialRepository,
        publisher: SyncEventPublisher,
    ) -> None:
        self._bank_fetch_service = bank_fetch_service
        self._opening_balance_service = opening_balance_service
        self._ml_classification_service = ml_classification_service
        self._import_service = import_service
        self._result_aggregator = result_aggregator
        self._period_resolver = period_resolver
        self._current_balance_service = current_balance_service
        self._bank_transaction_repo = bank_transaction_repo
        self._import_repo = import_repo
        self._credential_repo = credential_repo
        self._publisher = publisher

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_client: MLServiceClient,
        publisher: SyncEventPublisher,
    ) -> BankAccountSyncService:
        """Build the service and all its dependencies via the factory."""
        bank_fetch_service = BankFetchService.from_factory(factory)

        opening_balance_service = OpeningBalanceService(
            account_repository=factory.account_repository(),
            transaction_repository=factory.transaction_repository(),
            user_id=factory.current_user.user_id,
        )

        ml_classification_service = MLBatchClassificationService(
            ml_client=ml_client,
            current_user=factory.current_user,
        )

        import_service = TransactionImportService.from_factory(factory)

        result_aggregator = SyncResultAggregator()

        period_resolver = SyncPeriodResolver.from_factory(factory)

        current_balance_service = CurrentBalanceService.from_factory(factory)

        return cls(
            bank_fetch_service=bank_fetch_service,
            opening_balance_service=opening_balance_service,
            ml_classification_service=ml_classification_service,
            import_service=import_service,
            result_aggregator=result_aggregator,
            period_resolver=period_resolver,
            current_balance_service=current_balance_service,
            bank_transaction_repo=factory.bank_transaction_repository(),
            import_repo=factory.import_repository(),
            credential_repo=factory.credential_repository(),
            publisher=publisher,
        )

    async def sync_account(  # noqa: PLR0913
        self,
        mapping: AccountMapping,
        credentials: BankCredentials,
        period: SyncPeriod,
        auto_post: bool,
        account_index: int,
        total_accounts: int,
        tan_callback: Optional[TanCallback] = None,
    ) -> SyncResult:
        """Orchestrate sync for a single IBAN.

        Steps 1-14 from the design document.
        """
        # Step 1: Verify mapping is active
        if not mapping.is_active:
            msg = f"Account mapping for {mapping.iban} is inactive"
            raise InactiveMappingError(msg)

        # Step 2: Load TAN settings
        blz = extract_blz_from_iban(mapping.iban)
        tan_method: Optional[str] = None
        tan_medium: Optional[str] = None
        if blz:
            tan_method, tan_medium = await self._credential_repo.get_tan_settings(blz)

        # Step 3: Publish AccountSyncStarted
        await self._publisher.publish(
            AccountSyncStartedEvent(
                iban=mapping.iban,
                account_name=mapping.account_name,
                account_index=account_index,
                total_accounts=total_accounts,
            )
        )

        # Step 4: Resolve period (adaptive only when period.adaptive)
        if period.adaptive:
            resolved_period = await self._period_resolver.resolve_adaptive_for(
                mapping.iban
            )
        else:
            resolved_period = period

        # Step 5: Fetch bank transactions
        bank_transactions = await self._bank_fetch_service.fetch_transactions(
            credentials=credentials,
            iban=mapping.iban,
            period=resolved_period,
            tan_method=tan_method,
            tan_medium=tan_medium,
            tan_callback=tan_callback,
        )

        # Step 6: Save fetched with dedup
        stored_transactions = (
            await self._bank_transaction_repo.save_batch_with_deduplication(
                transactions=bank_transactions,
                account_iban=mapping.iban,
            )
        )

        # Step 7: Compute to_import
        to_import = [s for s in stored_transactions if s.is_new or not s.is_imported]

        # Step 8: Get current balance
        current_balance = await self._current_balance_service.for_iban(
            mapping.iban, credentials
        )

        # Step 9: Try opening balance creation
        if current_balance is not None:
            opening_balance = (
                await self._opening_balance_service.try_create_for_first_sync(
                    iban=mapping.iban,
                    current_balance=current_balance,
                    bank_transactions=bank_transactions,
                )
            )
        else:
            opening_balance = OpeningBalanceOutcome(created=False)

        # Step 10: Publish AccountSyncFetched
        await self._publisher.publish(
            AccountSyncFetchedEvent(
                iban=mapping.iban,
                transactions_fetched=len(bank_transactions),
                new_transactions=len(to_import),
            )
        )

        # Step 11: Empty-import early return
        if not to_import:
            logger.info(
                "All %d transactions already imported for %s, nothing new to do",
                len(bank_transactions),
                mapping.iban,
            )
            if blz:
                await self._credential_repo.update_last_used(blz)
            return self._result_aggregator.build(
                synced_at=utc_now(),
                iban=mapping.iban,
                period=resolved_period,
                bank_transactions=bank_transactions,
                import_results=[],
                opening_balance=opening_balance,
            )

        # Step 12: Classify via publisher
        preclassified = await self._classify_to_publisher(to_import, mapping.iban)

        # Step 13: Import streaming loop publishing TransactionClassified
        import_results = []
        async for current, total, result in self._import_service.import_streaming(
            stored_transactions=to_import,
            source_iban=mapping.iban,
            preclassified=preclassified,
            auto_post=auto_post,
        ):
            import_results.append(result)
            if result.is_success:
                await self._publisher.publish(
                    self._create_classified_event(mapping.iban, current, total, result)
                )

        # Step 14: Update last used and build result
        if blz:
            await self._credential_repo.update_last_used(blz)

        return self._result_aggregator.build(
            synced_at=utc_now(),
            iban=mapping.iban,
            period=resolved_period,
            bank_transactions=bank_transactions,
            import_results=import_results,
            opening_balance=opening_balance,
        )

    async def _classify_to_publisher(
        self,
        to_import: list,
        iban: str,
    ) -> dict[UUID, BatchClassificationResult]:
        """Drain ML classification stream: publish events, return results dict.

        Calls ``ml_classification_service.classify_batch_streaming`` and
        separates the yielded items: dict items become the preclassified
        return value; everything else (events) is published via the publisher.
        """
        preclassified: dict[UUID, BatchClassificationResult] = {}
        async for item in self._ml_classification_service.classify_batch_streaming(
            stored_transactions=to_import,
            iban=iban,
        ):
            if isinstance(item, dict):
                preclassified = item
            elif isinstance(
                item,
                (
                    ClassificationStartedEvent,
                    ClassificationProgressEvent,
                    ClassificationCompletedEvent,
                ),
            ):
                await self._publisher.publish(item)
        return preclassified

    @staticmethod
    def _create_classified_event(
        iban: str,
        current: int,
        total: int,
        result,
    ) -> TransactionClassifiedEvent:
        """Create a TransactionClassifiedEvent from an import result."""
        counter_account_name = ""
        if result.accounting_transaction:
            entries = result.accounting_transaction.entries
            if len(entries) >= 1:
                counter_account_name = entries[0].account.name

        return TransactionClassifiedEvent(
            iban=iban,
            current=current,
            total=total,
            description=result.bank_transaction.purpose or "",
            counter_account_name=counter_account_name,
            transaction_id=(
                result.accounting_transaction.id
                if result.accounting_transaction
                else None
            ),
        )
