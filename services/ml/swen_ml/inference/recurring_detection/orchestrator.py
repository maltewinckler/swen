"""Recurring detection orchestrator.

This orchestrator is stateless - it doesn't need SharedInfrastructure.
It provides a simple wrapper around the detect_recurring function.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from swen_ml_contracts import TransactionInput

from .detector import RecurringPattern, detect_recurring


@dataclass
class RecurringResult:
    """Result from recurring detection."""

    transaction_id: UUID
    is_recurring: bool
    pattern: RecurringPattern | None
    occurrences: int


class RecurringOrchestrator:
    """Application service for recurring transaction detection.

    This orchestrator is stateless - no dependencies needed.
    Provides a batch interface for detecting recurring patterns.
    """

    def detect(
        self,
        transactions: list[TransactionInput],
    ) -> list[RecurringResult]:
        """Detect recurring patterns in transactions.

        Args:
            transactions: Transactions to analyze

        Returns:
            List of RecurringResult, one per transaction
        """
        recurring = detect_recurring(transactions)

        results: list[RecurringResult] = []
        for txn in transactions:
            txn_id_str = str(txn.transaction_id)
            info = recurring.get(txn_id_str)

            results.append(
                RecurringResult(
                    transaction_id=txn.transaction_id,
                    is_recurring=info is not None,
                    pattern=info.pattern if info else None,
                    occurrences=info.occurrences if info else 0,
                )
            )

        return results
