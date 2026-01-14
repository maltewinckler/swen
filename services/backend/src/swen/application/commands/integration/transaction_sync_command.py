"""Sync bank transactions and import them into accounting."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps
from typing import TYPE_CHECKING, Awaitable, Callable, Optional

from swen.application.dtos.integration import (
    AccountClassifyingEvent,
    AccountFetchedEvent,
    SyncProgressEvent,
    SyncResult,
    TransactionClassifiedEvent,
)
from swen.application.services import TransactionImportService
from swen.domain.accounting.services import (
    OPENING_BALANCE_IBAN_KEY,
    OpeningBalanceService,
)
from swen.domain.banking.ports import BankConnectionPort
from swen.domain.banking.repositories import (
    BankAccountRepository,
    BankCredentialRepository,
    BankTransactionRepository,
)
from swen.domain.banking.value_objects import (
    BankCredentials,
    BankTransaction,
    TANChallenge,
)
from swen.domain.integration.repositories import (
    AccountMappingRepository,
    TransactionImportRepository,
)
from swen.domain.integration.value_objects import ImportStatus
from swen.domain.shared.iban import extract_blz_from_iban
from swen.domain.shared.time import utc_now
from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter
from swen.infrastructure.persistence.sqlalchemy.repositories.factory import (
    create_ai_provider_from_settings,
)

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )

logger = logging.getLogger(__name__)

TanCallback = Callable[[TANChallenge], str | Awaitable[str]]


@dataclass
class SyncRequest:
    """Request parameters for transaction sync operation."""

    iban: str
    credentials: Optional[BankCredentials] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tan_callback: Optional[TanCallback] = None


@dataclass
class _SyncContext:
    """Internal context for building sync result."""

    synced_at: datetime
    iban: str
    start_date: date
    end_date: date
    opening_balance_created: bool = False
    opening_balance_amount: Optional[Decimal] = None


class TransactionSyncCommand:
    """Coordinate bank fetch, TAN handling, import, and opening balance logic."""

    # Account number for the Opening Balance equity account
    OPENING_BALANCE_ACCOUNT_NUMBER = "2000"

    def __init__(  # noqa: PLR0913
        self,
        bank_adapter: BankConnectionPort,
        import_service: TransactionImportService,
        mapping_repo: AccountMappingRepository,
        import_repo: TransactionImportRepository,
        current_user: CurrentUser,
        credential_repo: Optional[BankCredentialRepository] = None,
        account_repo: Optional[AccountRepository] = None,
        transaction_repo: Optional[TransactionRepository] = None,
        bank_account_repo: Optional[BankAccountRepository] = None,
        bank_transaction_repo: Optional[BankTransactionRepository] = None,
    ):
        self._adapter = bank_adapter
        self._import_service = import_service
        self._mapping_repo = mapping_repo
        self._import_repo = import_repo
        self._user_id = current_user.user_id
        self._credential_repo = credential_repo
        self._account_repo = account_repo
        self._transaction_repo = transaction_repo
        self._bank_account_repo = bank_account_repo
        self._bank_transaction_repo = bank_transaction_repo
        self._opening_balance_service = OpeningBalanceService()

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> TransactionSyncCommand:
        ai_provider = create_ai_provider_from_settings()

        return cls(
            bank_adapter=GeldstromAdapter(),
            import_service=TransactionImportService.from_factory(factory, ai_provider),
            mapping_repo=factory.account_mapping_repository(),
            import_repo=factory.import_repository(),
            current_user=factory.current_user,
            credential_repo=factory.credential_repository(),
            account_repo=factory.account_repository(),
            transaction_repo=factory.transaction_repository(),
            bank_account_repo=factory.bank_account_repository(),
            bank_transaction_repo=factory.bank_transaction_repository(),
        )

    async def execute(  # noqa: PLR0913
        self,
        iban: str,
        credentials: Optional[BankCredentials] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        tan_callback: Optional[TanCallback] = None,
        auto_post: bool = False,
    ) -> SyncResult:
        synced_at = utc_now()

        try:
            credentials, credential_tracking = await self._resolve_credentials(
                credentials,
                iban,
            )

            mapping_check = await self._verify_account_mapping(iban)
            if not mapping_check["valid"]:
                return self._create_error_result(
                    synced_at,
                    iban,
                    start_date,
                    end_date,
                    mapping_check["error"],
                )

            start_date, end_date = await self._determine_sync_period(
                iban,
                start_date,
                end_date,
            )

            if (
                self._credential_repo
                and credential_tracking["loaded"]
                and credential_tracking["blz"]
            ):
                tan_method, tan_medium = await self._credential_repo.get_tan_settings(
                    credential_tracking["blz"],
                )
                if tan_method:
                    self._adapter.set_tan_method(tan_method)
                if tan_medium:
                    self._adapter.set_tan_medium(tan_medium)

            (
                bank_transactions,
                import_results,
                ob_created,
                ob_amount,
            ) = await self._perform_sync(
                credentials,
                iban,
                start_date,
                end_date,
                tan_callback,
                auto_post=auto_post,
            )

            await self._update_credential_usage(credential_tracking)

            context = _SyncContext(
                synced_at=synced_at,
                iban=iban,
                start_date=start_date,
                end_date=end_date,
                opening_balance_created=ob_created,
                opening_balance_amount=ob_amount,
            )
            return self._build_sync_result(
                context,
                bank_transactions,
                import_results,
            )

        except Exception as e:
            # Note: Disconnection is handled by _perform_sync's finally block
            # if the exception occurs during sync. For exceptions before sync
            # (e.g., credential loading), no connection has been established yet.
            return self._create_error_result(
                synced_at,
                iban,
                start_date,
                end_date,
                str(e),
            )

    async def _resolve_credentials(
        self,
        credentials: Optional[BankCredentials],
        iban: str,
    ) -> tuple[BankCredentials, dict]:
        tracking: dict = {"loaded": False, "blz": None}

        if credentials is None:
            credentials = await self._load_credentials(iban)
            tracking["loaded"] = True
            if credentials:
                tracking["blz"] = credentials.blz

        if credentials is None:
            msg = (
                "Could not resolve credentials. "
                "Provide credentials directly or ensure stored credentials exist."
            )
            raise ValueError(msg)

        return credentials, tracking

    async def _verify_account_mapping(self, iban: str) -> dict:
        mapping = await self._mapping_repo.find_by_iban(iban)

        if not mapping or not mapping.is_active:
            return {
                "valid": False,
                "error": f"No active account mapping found for {iban}",
            }

        return {"valid": True}

    async def _determine_sync_period(
        self,
        iban: str,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> tuple[date, date]:
        if start_date is None:
            start_date = await self._determine_default_start_date(iban)

        if end_date is None:
            end_date = date.today()

        start_date = min(start_date, end_date)

        return start_date, end_date

    async def _perform_sync(  # NOQA: PLR0913
        self,
        credentials: BankCredentials,
        iban: str,
        start_date: date,
        end_date: date,
        tan_callback: Optional[TanCallback],
        auto_post: bool = False,
    ) -> tuple[list, list, bool, Decimal | None]:
        """Perform the actual sync: connect, fetch, import, disconnect.

        Two-phase sync flow:
        1. Fetch transactions from bank
        2. Save to bank_transactions table (with hash+sequence deduplication)
        3. Create opening balance if first sync
        4. Import only NEW (un-imported) transactions to accounting

        This properly handles identical transactions (e.g., two refunds of €3.10
        on the same day with the same purpose) by using sequence numbers.

        Returns
        -------
        Tuple of (
            bank_transactions,
            import_results,
            opening_balance_created,
            opening_balance_amount,
        )
        """
        if tan_callback:
            await self._adapter.set_tan_callback(
                self._wrap_tan_callback(tan_callback),
            )

        await self._adapter.connect(credentials)

        try:
            await self._update_bank_accounts()

            bank_transactions = await self._adapter.fetch_transactions(
                account_iban=iban,
                start_date=start_date,
                end_date=end_date,
            )

            ob_created, ob_amount = await self._try_create_opening_balance(
                iban=iban,
                bank_transactions=bank_transactions,
            )

            # Phase 1: Save to bank_transactions table with deduplication
            # This handles identical transactions via hash + sequence
            if not self._bank_transaction_repo:
                msg = "bank_transaction_repo is required for sync"
                raise RuntimeError(msg)

            stored_results = (
                await self._bank_transaction_repo.save_batch_with_deduplication(
                    bank_transactions,
                    iban,
                )
            )

            # Filter for transactions that need importing:
            # - New transactions (just stored)
            # - Existing transactions that were never imported (previous sync failed)
            to_import = [r for r in stored_results if r.is_new or not r.is_imported]

            if not to_import:
                logger.info(
                    "All %d transactions already imported, nothing new to do",
                    len(bank_transactions),
                )
                return bank_transactions, [], ob_created, ob_amount

            new_count = sum(1 for r in to_import if r.is_new)
            retry_count = len(to_import) - new_count
            logger.info(
                "Will import %d transactions (%d new, %d retry)",
                len(to_import),
                new_count,
                retry_count,
            )

            # Phase 2: Import transactions to accounting
            import_results = await self._import_service.import_from_stored_transactions(
                stored_transactions=to_import,
                source_iban=iban,
                auto_post=auto_post,
            )

            return bank_transactions, import_results, ob_created, ob_amount

        finally:
            # Always disconnect
            await self._adapter.disconnect()

    async def _perform_sync_streaming(  # NOQA: PLR0913
        self,
        credentials: BankCredentials,
        iban: str,
        start_date: date,
        end_date: date,
        tan_callback: Optional[TanCallback],
        auto_post: bool = False,
    ):
        """Perform sync with progress events yielded after each transaction.

        This is an async generator that yields SyncProgressEvent objects,
        enabling real-time feedback to the frontend via SSE.

        Yields
        ------
        SyncProgressEvent subclasses for each stage of the sync.

        Returns (via final yield):
        Tuple of (bank_transactions, import_results, ob_created, ob_amount)
        """
        if tan_callback:
            await self._adapter.set_tan_callback(
                self._wrap_tan_callback(tan_callback),
            )

        await self._adapter.connect(credentials)

        try:
            await self._update_bank_accounts()

            bank_transactions = await self._adapter.fetch_transactions(
                account_iban=iban,
                start_date=start_date,
                end_date=end_date,
            )

            ob_created, ob_amount = await self._try_create_opening_balance(
                iban=iban,
                bank_transactions=bank_transactions,
            )

            # Phase 1: Save to bank_transactions table with deduplication
            if not self._bank_transaction_repo:
                msg = "bank_transaction_repo is required for sync"
                raise RuntimeError(msg)

            stored_results = (
                await self._bank_transaction_repo.save_batch_with_deduplication(
                    bank_transactions,
                    iban,
                )
            )

            # Filter for transactions that need importing:
            # - New transactions (just stored)
            # - Existing transactions that were never imported (previous sync failed)
            to_import = [r for r in stored_results if r.is_new or not r.is_imported]

            # Yield fetched event
            yield AccountFetchedEvent(
                iban=iban,
                transactions_fetched=len(bank_transactions),
                new_transactions=len(to_import),
            )

            if not to_import:
                logger.info(
                    "All %d transactions already imported, nothing new to do",
                    len(bank_transactions),
                )
                # Yield final result tuple
                yield (bank_transactions, [], ob_created, ob_amount)
                return

            new_count = sum(1 for r in to_import if r.is_new)
            retry_count = len(to_import) - new_count
            logger.info(
                "Will import %d transactions (%d new, %d retry)",
                len(to_import),
                new_count,
                retry_count,
            )

            # Yield classifying start event
            yield AccountClassifyingEvent(
                iban=iban,
                current=0,
                total=len(to_import),
            )

            # Phase 2: Import transactions to accounting (streaming)
            import_results = []
            async for (
                current,
                total,
                result,
            ) in self._import_service.import_from_stored_transactions_streaming(
                stored_transactions=to_import,
                source_iban=iban,
                auto_post=auto_post,
            ):
                import_results.append(result)

                # Yield progress for each transaction
                if result.status == ImportStatus.SUCCESS:
                    counter_account_name = ""
                    if result.accounting_transaction:
                        # Get counter account from journal entries
                        # Entry order:
                        # [0] = counter_account (expense/income),
                        # [1] = asset_account (bank)
                        entries = result.accounting_transaction.entries
                        if len(entries) >= 1:
                            counter_account_name = entries[0].account.name

                    yield TransactionClassifiedEvent(
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

            # Yield final result tuple
            yield (bank_transactions, import_results, ob_created, ob_amount)

        finally:
            # Always disconnect
            await self._adapter.disconnect()

    async def execute_streaming(  # NOQA: PLR0913
        self,
        iban: str,
        credentials: Optional[BankCredentials] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        tan_callback: Optional[TanCallback] = None,
        auto_post: bool = False,
    ):
        """Execute transaction sync with streaming progress events.

        This is an async generator that yields SyncProgressEvent objects,
        enabling real-time feedback to the frontend via SSE.
        """
        synced_at = utc_now()

        try:
            credentials, credential_tracking = await self._resolve_credentials(
                credentials,
                iban,
            )

            mapping_check = await self._verify_account_mapping(iban)
            if not mapping_check["valid"]:
                yield self._create_error_result(
                    synced_at,
                    iban,
                    start_date,
                    end_date,
                    mapping_check["error"],
                )
                return

            start_date, end_date = await self._determine_sync_period(
                iban,
                start_date,
                end_date,
            )

            if (
                self._credential_repo
                and credential_tracking["loaded"]
                and credential_tracking["blz"]
            ):
                tan_method, tan_medium = await self._credential_repo.get_tan_settings(
                    credential_tracking["blz"],
                )
                if tan_method:
                    self._adapter.set_tan_method(tan_method)
                if tan_medium:
                    self._adapter.set_tan_medium(tan_medium)

            bank_transactions = []
            import_results = []
            ob_created = False
            ob_amount = None

            async for event in self._perform_sync_streaming(
                credentials,
                iban,
                start_date,
                end_date,
                tan_callback,
                auto_post=auto_post,
            ):
                if isinstance(event, SyncProgressEvent):
                    yield event
                elif isinstance(event, tuple):
                    bank_transactions, import_results, ob_created, ob_amount = event

            await self._update_credential_usage(credential_tracking)

            context = _SyncContext(
                synced_at=synced_at,
                iban=iban,
                start_date=start_date,
                end_date=end_date,
                opening_balance_created=ob_created,
                opening_balance_amount=ob_amount,
            )
            yield self._build_sync_result(
                context,
                bank_transactions,
                import_results,
            )

        except Exception as e:
            logger.exception("Sync failed for %s: %s", iban, e)
            yield self._create_error_result(
                synced_at,
                iban,
                start_date,
                end_date,
                str(e),
            )

    async def _try_create_opening_balance(
        self,
        iban: str,
        bank_transactions: list[BankTransaction],
    ) -> tuple[bool, Decimal | None]:
        """
        Try to create opening balance if this is the first sync.

        Opening balance is only created when:
        1. We have the required repositories (account_repo, transaction_repo)
        2. We have transactions to import (need dates for calculation)
        3. No opening balance already exists for this IBAN
        4. We can get the current balance from the bank
        """
        if not self._account_repo or not self._transaction_repo:
            logger.debug(
                "Skip opening balance: account_repo or transaction_repo not provided",
            )
            return (False, None)

        if not bank_transactions:
            logger.debug("Skip opening balance: no transactions to import")
            return (False, None)

        if await self._has_opening_balance(iban):
            logger.debug("Opening balance already exists for IBAN %s", iban)
            return (False, None)

        current_balance = await self._get_current_balance(iban)
        if current_balance is None:
            logger.warning(
                "Cannot create opening balance: current balance not available for %s",
                iban,
            )
            return (False, None)

        return await self._create_opening_balance(
            iban=iban,
            current_balance=current_balance,
            bank_transactions=bank_transactions,
        )

    async def _has_opening_balance(self, iban: str) -> bool:
        if not self._transaction_repo:
            return False

        existing = await self._transaction_repo.find_by_metadata(
            metadata_key=OPENING_BALANCE_IBAN_KEY,
            metadata_value=iban,
        )
        return len(existing) > 0

    async def _update_bank_accounts(self) -> None:
        if not self._bank_account_repo:
            return

        try:
            accounts = await self._adapter.fetch_accounts()
            for account in accounts:
                await self._bank_account_repo.save(account)
            logger.debug("Updated %d bank accounts in database", len(accounts))
        except Exception as e:
            # Don't fail the sync if bank account update fails
            logger.warning("Failed to update bank accounts: %s", e)

    async def _get_current_balance(self, iban: str) -> Decimal | None:
        accounts = await self._adapter.fetch_accounts()

        for account in accounts:
            if account.iban == iban and account.balance is not None:
                return account.balance

        return None

    async def _create_opening_balance(
        self,
        iban: str,
        current_balance: Decimal,
        bank_transactions: list[BankTransaction],
    ) -> tuple[bool, Decimal | None]:
        if not self._account_repo or not self._transaction_repo:
            return (False, None)

        try:
            accounts = await self._get_opening_balance_accounts(iban)
            if accounts is None:
                return (False, None)

            asset_account, opening_balance_account = accounts

            result = self._prepare_opening_balance_data(
                current_balance,
                bank_transactions,
            )
            if result is None:
                return (False, None)

            opening_balance, balance_date, currency = result

            txn = self._opening_balance_service.create_opening_balance_transaction(
                asset_account=asset_account,
                opening_balance_account=opening_balance_account,
                amount=opening_balance,
                currency=currency,
                balance_date=balance_date,
                iban=iban,
                user_id=self._user_id,
            )

            if txn is None:
                logger.info(
                    "Opening balance is zero for %s; skipping",
                    iban,
                )
                return (False, None)

            await self._transaction_repo.save(txn)
            logger.info(
                "Created opening balance of %s %s for %s (date: %s)",
                opening_balance,
                currency,
                iban,
                balance_date.date(),
            )
            return (True, opening_balance)

        except Exception as e:
            logger.error("Failed to create opening balance for %s: %s", iban, e)
            return (False, None)

    async def _get_opening_balance_accounts(self, iban: str):
        if not self._account_repo:
            return None

        mapping = await self._mapping_repo.find_by_iban(iban)
        if not mapping:
            logger.warning(
                "Cannot create opening balance: no account mapping found for %s",
                iban,
            )
            return None

        asset_account = await self._account_repo.find_by_id(
            mapping.accounting_account_id,
        )
        if not asset_account:
            logger.warning(
                "Cannot create opening balance: mapped asset account not found for %s",
                iban,
            )
            return None

        opening_balance_account = await self._account_repo.find_by_account_number(
            self.OPENING_BALANCE_ACCOUNT_NUMBER,
        )
        if not opening_balance_account:
            logger.warning(
                "Cannot create opening balance: equity account %s not found.",
                self.OPENING_BALANCE_ACCOUNT_NUMBER,
            )
            return None

        return asset_account, opening_balance_account

    def _prepare_opening_balance_data(
        self,
        current_balance: Decimal,
        bank_transactions: list[BankTransaction],
    ):
        opening_balance = self._opening_balance_service.calculate_opening_balance(
            current_balance=current_balance,
            bank_transactions=bank_transactions,
        )

        balance_date = self._opening_balance_service.get_earliest_transaction_date(
            bank_transactions,
        )
        if not balance_date:
            logger.warning("Cannot determine date for opening balance")
            return None

        currency = bank_transactions[0].currency if bank_transactions else "EUR"
        return opening_balance, balance_date, currency

    async def _update_credential_usage(self, tracking: dict) -> None:
        """Update credential last_used timestamp if loaded from storage."""
        if tracking["loaded"] and self._credential_repo and tracking["blz"]:
            # Credential repository is user-scoped
            await self._credential_repo.update_last_used(
                tracking["blz"],
            )

    def _build_sync_result(
        self,
        context: _SyncContext,
        bank_transactions: list,
        import_results: list,
    ) -> SyncResult:
        stats = self._calculate_import_statistics(import_results, bank_transactions)

        return SyncResult(
            success=stats["success"],
            synced_at=context.synced_at,
            iban=context.iban,
            start_date=context.start_date,
            end_date=context.end_date,
            transactions_fetched=len(bank_transactions),
            transactions_imported=stats["imported"],
            transactions_skipped=stats["skipped"],
            transactions_failed=stats["failed"],
            transactions_reconciled=stats.get("reconciled", 0),
            error_message=stats["error_message"],
            warning_message=stats["warning_message"],
            opening_balance_created=context.opening_balance_created,
            opening_balance_amount=context.opening_balance_amount,
        )

    def _calculate_import_statistics(
        self,
        import_results: list,
        bank_transactions: list,
    ) -> dict:
        counts = self._count_import_results(import_results)
        messages = self._build_result_messages(counts, bank_transactions)
        return {**counts, **messages}

    def _count_import_results(self, import_results: list) -> dict:
        imported = 0
        skipped = 0
        failed = 0
        reconciled = 0
        error_details = []

        for result in import_results:
            status = self._coerce_status(result)

            if status == ImportStatus.SUCCESS:
                imported += 1
                if hasattr(result, "was_reconciled") and result.was_reconciled:
                    reconciled += 1
            elif status in (ImportStatus.DUPLICATE, ImportStatus.SKIPPED):
                skipped += 1
            elif status == ImportStatus.FAILED:
                failed += 1
                if hasattr(result, "error_message") and result.error_message:
                    error_details.append(result.error_message)

        return {
            "imported": imported,
            "skipped": skipped,
            "failed": failed,
            "reconciled": reconciled,
            "error_details": error_details,
        }

    def _build_result_messages(self, counts: dict, bank_transactions: list) -> dict:
        failed = counts["failed"]
        imported = counts["imported"]
        skipped = counts["skipped"]
        reconciled = counts["reconciled"]
        error_details = counts["error_details"]

        has_failures = failed > 0
        has_positive_outcome = imported > 0 or skipped > 0 or not bank_transactions
        success_flag = not has_failures or has_positive_outcome

        warning_message = self._build_warning_message(
            has_failures,
            success_flag,
            failed,
            error_details,
            reconciled,
        )
        error_message = self._build_error_message(
            has_failures,
            success_flag,
            failed,
            error_details,
        )

        return {
            "success": success_flag,
            "warning_message": warning_message,
            "error_message": error_message,
        }

    def _build_warning_message(
        self,
        has_failures: bool,
        success_flag: bool,
        failed: int,
        error_details: list,
        reconciled: int,
    ) -> str | None:
        warning_message = None

        if has_failures and success_flag:
            warning_message = self._format_failure_message(failed, error_details)

        if reconciled > 0:
            reconcile_msg = (
                f"Reconciled {reconciled} internal transfer"
                f"{'s' if reconciled != 1 else ''} with existing transactions"
            )
            if warning_message:
                warning_message = f"{warning_message}. {reconcile_msg}"
            else:
                warning_message = reconcile_msg

        return warning_message

    def _build_error_message(
        self,
        has_failures: bool,
        success_flag: bool,
        failed: int,
        error_details: list,
    ) -> str | None:
        if has_failures and not success_flag:
            return self._format_failure_message(failed, error_details)
        return None

    @staticmethod
    def _format_failure_message(failed_count: int, error_details: list[str]) -> str:
        """Format failure message with error details."""
        failure_msg = (
            f"{failed_count} transaction{'s' if failed_count != 1 else ''} "
            "failed to import"
        )

        if error_details:
            sample_errors = error_details[:3]
            failure_msg += ": " + "; ".join(sample_errors)
            if len(error_details) > 3:
                failure_msg += f" (and {len(error_details) - 3} more)"

        return failure_msg

    def _create_error_result(
        self,
        synced_at: datetime,
        iban: str,
        start_date: Optional[date],
        end_date: Optional[date],
        error_message: str,
    ) -> SyncResult:
        """Create a SyncResult for error scenarios."""
        return SyncResult(
            success=False,
            synced_at=synced_at,
            iban=iban,
            start_date=start_date or date.today(),
            end_date=end_date or date.today(),
            transactions_fetched=0,
            transactions_imported=0,
            transactions_skipped=0,
            transactions_failed=0,
            error_message=error_message,
        )

    async def _load_credentials(
        self,
        iban: str,
    ) -> Optional[BankCredentials]:
        """Load stored credentials for the account.

        The credentials are loaded using a user-scoped repository,
        so only the current user's credentials are accessible.

        Parameters
        ----------
        iban
            IBAN to determine BLZ

        Returns
        -------
        Loaded credentials or None if not found

        Raises
        ------
        ValueError
            If credential repository not available
        """
        if not self._credential_repo:
            msg = (
                "Cannot load stored credentials: credential_repo not provided. "
                "Pass credential_repo to __init__ or provide credentials directly."
            )
            raise ValueError(msg)

        blz = extract_blz_from_iban(iban)
        if blz is None:
            msg = f"Cannot extract BLZ from IBAN {iban}"
            raise ValueError(msg)

        # Load credentials (repository is user-scoped)
        credentials = await self._credential_repo.find_by_blz(blz)

        if not credentials:
            msg = (
                f"No stored credentials found for BLZ {blz}. "
                f"Store credentials first using StoreCredentialsCommand."
            )
            raise ValueError(msg)

        return credentials

    async def _determine_default_start_date(self, iban: str) -> date:
        """Compute default sync window start date based on import history."""
        imports = await self._import_repo.find_by_iban(iban)

        candidate_dates: list[date] = []
        for record in imports:
            if record.status != ImportStatus.SUCCESS:
                continue

            booking_date = self._extract_booking_date(record)
            if booking_date:
                candidate_dates.append(booking_date)
            elif record.imported_at:
                candidate_dates.append(record.imported_at.date())

        if not candidate_dates:
            return date.today() - timedelta(days=90)

        last_booking_date = max(candidate_dates)
        today = date.today()
        next_sync_start = last_booking_date + timedelta(days=1)

        if next_sync_start > today:
            return today

        return next_sync_start

    @staticmethod
    def _extract_booking_date(record) -> Optional[date]:
        """Try to extract booking date from transaction identity hash."""
        identity = getattr(record, "bank_transaction_identity", "")
        parts = identity.split("|")

        if len(parts) < 2:
            return None

        try:
            return date.fromisoformat(parts[1])
        except ValueError:
            return None

    @staticmethod
    def _coerce_status(result) -> Optional[ImportStatus]:
        """Normalize status value from import result mocks or domain objects."""
        status = getattr(result, "status", None)

        if isinstance(status, ImportStatus):
            return status

        if isinstance(status, str):
            normalized = status.lower()
            mapping = {
                "imported": ImportStatus.SUCCESS,
                "success": ImportStatus.SUCCESS,
                "duplicate": ImportStatus.DUPLICATE,
                "skipped_duplicate": ImportStatus.DUPLICATE,
                "skipped": ImportStatus.SKIPPED,
                "failed": ImportStatus.FAILED,
            }
            return mapping.get(normalized)

        return None

    @staticmethod
    def _wrap_tan_callback(
        callback: TanCallback,
    ) -> Callable[[TANChallenge], Awaitable[str]]:
        """Ensure TAN callback can be awaited even if sync."""

        @wraps(callback)
        async def _async_callback(challenge: TANChallenge) -> str:
            result = callback(challenge)
            if inspect.isawaitable(result):
                return await result  # type: ignore[func-returns-value]
            return result  # type: ignore[return-value,arg-type]

        return _async_callback
