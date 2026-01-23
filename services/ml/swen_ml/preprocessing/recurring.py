"""Recurring pattern detection."""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import numpy as np
from swen_ml_contracts import TransactionInput

from swen_ml.preprocessing.merchant import normalize_counterparty

RecurringPattern = Literal["monthly", "weekly"]


@dataclass
class RecurringInfo:
    """Information about a recurring transaction pattern."""

    pattern: RecurringPattern
    occurrences: int
    transaction_ids: list[str]


def detect_recurring_batch(
    transactions: list[TransactionInput],
) -> dict[str, RecurringInfo]:
    """Detect recurring patterns in a batch of transactions.

    Groups transactions by (normalized_counterparty, amount) and checks
    if the booking dates follow a regular interval.

    Returns:
        Dict mapping transaction_id -> RecurringInfo for recurring transactions.
    """
    # Group by (counterparty, amount)
    groups: dict[tuple[str, Decimal], list[TransactionInput]] = defaultdict(list)

    for txn in transactions:
        key = (normalize_counterparty(txn.counterparty_name), txn.amount)
        groups[key].append(txn)

    # Check each group for recurring pattern
    recurring: dict[str, RecurringInfo] = {}

    for (counterparty, amount), txns in groups.items():
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


def _detect_pattern(txns: list[TransactionInput]) -> RecurringPattern | None:
    """Detect if transactions follow a regular pattern."""
    dates = sorted(txn.booking_date for txn in txns)

    if len(dates) < 2:
        return None

    # Compute intervals in days
    intervals = [
        (dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)
    ]

    median_interval = np.median(intervals)

    # Monthly: 25-35 days
    if 25 <= median_interval <= 35:
        return "monthly"

    # Weekly: 6-8 days
    if 6 <= median_interval <= 8:
        return "weekly"

    return None
