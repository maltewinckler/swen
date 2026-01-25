"""Recurring pattern detection for transactions."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

import numpy as np
from swen_ml_contracts import TransactionInput

RecurringPattern = Literal["monthly", "weekly"]


@dataclass
class RecurringInfo:
    """Information about a recurring transaction pattern."""

    pattern: RecurringPattern
    occurrences: int
    transaction_ids: list[str]


def normalize_counterparty(counterparty: str | None) -> str:
    """Normalize counterparty for comparison."""
    if not counterparty:
        return ""
    return re.sub(r"[^a-zA-ZäöüÄÖÜß0-9]", "", counterparty.lower())


def detect_recurring(
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
