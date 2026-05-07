"""Unit tests for SyncResultAggregator.

Covers:
- Statistics counting: imported, skipped, failed, reconciled
- Warning message construction (partial failures with positive outcome)
- Error message construction (all-failure case)
- Reconciliation message appended to warning
- Multiple error details sampled (up to _MAX_SAMPLE_ERRORS)
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from swen.application.dtos.integration.sync_period import SyncPeriod
from swen.application.services.integration.sync_result_aggregator import (
    SyncResultAggregator,
)
from swen.application.services.transaction_import_service import TransactionImportResult
from swen.domain.accounting.services.opening_balance.service import (
    OpeningBalanceOutcome,
)
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.value_objects import ImportStatus

TEST_IBAN = "DE89370400440532013000"
_SYNCED_AT = datetime(2024, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
_PERIOD = SyncPeriod(
    start_date=date(2024, 6, 1),
    end_date=date(2024, 6, 15),
    adaptive=False,
)
_NO_OB = OpeningBalanceOutcome(created=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_bank_tx() -> BankTransaction:
    return BankTransaction(
        booking_date=date(2024, 6, 10),
        value_date=date(2024, 6, 10),
        amount=Decimal("100.00"),
        currency="EUR",
        purpose="Test",
    )


def _make_result(
    status: ImportStatus,
    *,
    error_message: str | None = None,
    was_reconciled: bool = False,
) -> TransactionImportResult:
    return TransactionImportResult(
        bank_transaction=_make_bank_tx(),
        status=status,
        error_message=error_message,
        was_reconciled=was_reconciled,
    )


def _build(
    import_results: list[TransactionImportResult],
    bank_transactions: list[BankTransaction] | None = None,
    opening_balance: OpeningBalanceOutcome = _NO_OB,
):
    if bank_transactions is None:
        bank_transactions = [_make_bank_tx() for _ in import_results]
    return SyncResultAggregator.build(
        synced_at=_SYNCED_AT,
        iban=TEST_IBAN,
        period=_PERIOD,
        bank_transactions=bank_transactions,
        import_results=import_results,
        opening_balance=opening_balance,
    )


# ---------------------------------------------------------------------------
# Statistics counting
# ---------------------------------------------------------------------------


class TestStatisticsCounting:
    """Counts are correctly aggregated from import results."""

    def test_all_success(self):
        results = [_make_result(ImportStatus.SUCCESS) for _ in range(3)]
        sync_result = _build(results)

        assert sync_result.transactions_imported == 3
        assert sync_result.transactions_skipped == 0
        assert sync_result.transactions_failed == 0

    def test_all_duplicate_counted_as_skipped(self):
        results = [_make_result(ImportStatus.DUPLICATE) for _ in range(2)]
        sync_result = _build(results)

        assert sync_result.transactions_skipped == 2
        assert sync_result.transactions_imported == 0

    def test_all_skipped(self):
        results = [_make_result(ImportStatus.SKIPPED) for _ in range(2)]
        sync_result = _build(results)

        assert sync_result.transactions_skipped == 2

    def test_all_failed(self):
        results = [
            _make_result(ImportStatus.FAILED, error_message="err") for _ in range(2)
        ]
        sync_result = _build(results)

        assert sync_result.transactions_failed == 2
        assert sync_result.transactions_imported == 0

    def test_mixed_statuses(self):
        results = [
            _make_result(ImportStatus.SUCCESS),
            _make_result(ImportStatus.SUCCESS),
            _make_result(ImportStatus.DUPLICATE),
            _make_result(ImportStatus.FAILED, error_message="oops"),
        ]
        sync_result = _build(results)

        assert sync_result.transactions_imported == 2
        assert sync_result.transactions_skipped == 1
        assert sync_result.transactions_failed == 1

    def test_reconciled_counted_within_imported(self):
        results = [
            _make_result(ImportStatus.SUCCESS, was_reconciled=True),
            _make_result(ImportStatus.SUCCESS, was_reconciled=False),
        ]
        sync_result = _build(results)

        assert sync_result.transactions_imported == 2
        assert sync_result.transactions_reconciled == 1

    def test_fetched_count_matches_bank_transactions(self):
        bank_txs = [_make_bank_tx() for _ in range(5)]
        sync_result = _build([], bank_transactions=bank_txs)

        assert sync_result.transactions_fetched == 5

    def test_empty_results_all_zeros(self):
        sync_result = _build([])

        assert sync_result.transactions_imported == 0
        assert sync_result.transactions_skipped == 0
        assert sync_result.transactions_failed == 0
        assert sync_result.transactions_reconciled == 0


# ---------------------------------------------------------------------------
# Success flag
# ---------------------------------------------------------------------------


class TestSuccessFlag:
    """success is True when there are no failures or when some imports succeeded."""

    def test_success_true_when_all_imported(self):
        results = [_make_result(ImportStatus.SUCCESS)]
        sync_result = _build(results)
        assert sync_result.success is True

    def test_success_true_when_partial_failure_but_some_imported(self):
        results = [
            _make_result(ImportStatus.SUCCESS),
            _make_result(ImportStatus.FAILED, error_message="err"),
        ]
        sync_result = _build(results)
        assert sync_result.success is True

    def test_success_false_when_all_failed_and_nothing_imported(self):
        results = [
            _make_result(ImportStatus.FAILED, error_message="err1"),
            _make_result(ImportStatus.FAILED, error_message="err2"),
        ]
        sync_result = _build(
            results, bank_transactions=[_make_bank_tx(), _make_bank_tx()]
        )
        assert sync_result.success is False

    def test_success_true_when_no_transactions_fetched(self):
        sync_result = _build([], bank_transactions=[])
        assert sync_result.success is True


# ---------------------------------------------------------------------------
# Warning message construction
# ---------------------------------------------------------------------------


class TestWarningMessage:
    """Warning message is set when there are partial failures."""

    def test_warning_message_set_on_partial_failure(self):
        results = [
            _make_result(ImportStatus.SUCCESS),
            _make_result(ImportStatus.FAILED, error_message="bad tx"),
        ]
        sync_result = _build(results)

        assert sync_result.warning_message is not None
        assert "failed" in sync_result.warning_message.lower()

    def test_warning_message_none_when_all_success(self):
        results = [_make_result(ImportStatus.SUCCESS)]
        sync_result = _build(results)

        assert sync_result.warning_message is None

    def test_warning_message_includes_failure_count(self):
        results = [
            _make_result(ImportStatus.SUCCESS),
            _make_result(ImportStatus.FAILED, error_message="err1"),
            _make_result(ImportStatus.FAILED, error_message="err2"),
        ]
        sync_result = _build(results)

        assert sync_result.warning_message is not None
        assert "2" in sync_result.warning_message

    def test_warning_message_includes_reconciliation_info(self):
        results = [
            _make_result(ImportStatus.SUCCESS, was_reconciled=True),
        ]
        sync_result = _build(results)

        assert sync_result.warning_message is not None
        assert "reconcil" in sync_result.warning_message.lower()

    def test_warning_message_none_when_no_reconciliation_and_no_failures(self):
        results = [_make_result(ImportStatus.SUCCESS, was_reconciled=False)]
        sync_result = _build(results)

        assert sync_result.warning_message is None


# ---------------------------------------------------------------------------
# Error message construction
# ---------------------------------------------------------------------------


class TestErrorMessage:
    """Error message is set when all imports failed."""

    def test_error_message_set_when_all_failed(self):
        results = [
            _make_result(ImportStatus.FAILED, error_message="err1"),
            _make_result(ImportStatus.FAILED, error_message="err2"),
        ]
        sync_result = _build(
            results, bank_transactions=[_make_bank_tx(), _make_bank_tx()]
        )

        assert sync_result.error_message is not None
        assert "failed" in sync_result.error_message.lower()

    def test_error_message_none_on_partial_failure(self):
        results = [
            _make_result(ImportStatus.SUCCESS),
            _make_result(ImportStatus.FAILED, error_message="err"),
        ]
        sync_result = _build(results)

        assert sync_result.error_message is None

    def test_error_message_none_when_all_success(self):
        results = [_make_result(ImportStatus.SUCCESS)]
        sync_result = _build(results)

        assert sync_result.error_message is None

    def test_error_message_samples_up_to_three_errors(self):
        """Only the first 3 error details are included in the message."""
        results = [
            _make_result(ImportStatus.FAILED, error_message=f"error {i}")
            for i in range(5)
        ]
        sync_result = _build(
            results,
            bank_transactions=[_make_bank_tx() for _ in range(5)],
        )

        # Should mention "and 2 more" since 5 errors but only 3 sampled
        assert sync_result.error_message is not None
        assert "more" in sync_result.error_message


# ---------------------------------------------------------------------------
# Opening balance fields
# ---------------------------------------------------------------------------


class TestOpeningBalanceFields:
    """Opening balance outcome is reflected in the SyncResult."""

    def test_opening_balance_created_true_when_outcome_created(self):
        ob = OpeningBalanceOutcome(created=True, amount=Decimal("800.00"))
        sync_result = _build([], opening_balance=ob)

        assert sync_result.opening_balance_created is True
        assert sync_result.opening_balance_amount == Decimal("800.00")

    def test_opening_balance_created_false_when_outcome_not_created(self):
        sync_result = _build([], opening_balance=_NO_OB)

        assert sync_result.opening_balance_created is False
        assert sync_result.opening_balance_amount is None


# ---------------------------------------------------------------------------
# Period and metadata fields
# ---------------------------------------------------------------------------


class TestMetadataFields:
    """Period dates, IBAN, and synced_at are passed through correctly."""

    def test_iban_matches(self):
        sync_result = _build([])
        assert sync_result.iban == TEST_IBAN

    def test_start_date_matches_period(self):
        sync_result = _build([])
        assert sync_result.start_date == _PERIOD.start_date

    def test_end_date_matches_period(self):
        sync_result = _build([])
        assert sync_result.end_date == _PERIOD.end_date

    def test_synced_at_matches(self):
        sync_result = _build([])
        assert sync_result.synced_at == _SYNCED_AT
