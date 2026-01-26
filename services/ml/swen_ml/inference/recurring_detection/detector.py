from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

import numpy as np
from swen_ml_contracts import TransactionInput

RecurringPattern = Literal["monthly", "weekly"]


@dataclass
class RecurringInfo:
    """Information about a recurring transaction pattern."""

    pattern: RecurringPattern
    occurrences: int
    transaction_ids: list[str]


@dataclass
class RecurringResult:
    """Result from recurring detection for a single transaction."""

    transaction_id: UUID
    is_recurring: bool
    pattern: RecurringPattern | None
    occurrences: int


def _normalize_counterparty(counterparty: str | None) -> str:
    """Normalize counterparty for comparison."""
    if not counterparty:
        return ""
    return re.sub(r"[^a-zA-ZäöüÄÖÜß0-9]", "", counterparty.lower())


def _detect_pattern(txns: list[TransactionInput]) -> RecurringPattern | None:
    """Detect if transactions follow a regular pattern."""
    dates = sorted(txn.booking_date for txn in txns)

    if len(dates) < 2:
        return None

    # Compute intervals in days
    intervals = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]

    median_interval = float(np.median(intervals))

    # Monthly: 25-35 days
    if 25 <= median_interval <= 35:
        return "monthly"

    # Weekly: 6-8 days
    if 6 <= median_interval <= 8:
        return "weekly"

    return None


class RecurringDetector:
    """Detector for recurring transaction patterns."""

    def detect(self, transactions: list[TransactionInput]) -> list[RecurringResult]:
        recurring = self._find_recurring(transactions)

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

    def _find_recurring(
        self, transactions: list[TransactionInput]
    ) -> dict[str, RecurringInfo]:
        groups: dict[tuple[str, Decimal], list[TransactionInput]] = defaultdict(list)

        for txn in transactions:
            key = (_normalize_counterparty(txn.counterparty_name), txn.amount)
            groups[key].append(txn)

        # Check each group for recurring pattern
        recurring: dict[str, RecurringInfo] = {}

        for (_counterparty, _amount), txns in groups.items():
            if len(txns) < 2:
                continue

            pattern = _detect_pattern(txns)
            if pattern:
                info = RecurringInfo(
                    pattern=pattern,
                    occurrences=len(txns),
                    transaction_ids=[str(t.transaction_id) for t in txns],
                )
                for txn in txns:
                    recurring[str(txn.transaction_id)] = info

        return recurring
