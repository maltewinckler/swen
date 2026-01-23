"""Pattern matching tier (Tier 1)."""

import numpy as np
from swen_ml_contracts import AccountOption, TransactionInput

from swen_ml.config.patterns import KEYWORDS, KNOWN_MERCHANTS, normalize_merchant
from swen_ml.pipeline.tiers.base import BatchTierResult, TierResult


def pattern_match_batch(
    transactions: list[TransactionInput],
    accounts: list[AccountOption],
) -> BatchTierResult:
    """Match transactions against known merchant patterns and keywords.

    This is a fast, high-confidence tier using dict lookups.
    """
    n = len(transactions)
    results: list[TierResult | None] = [None] * n
    classified = np.zeros(n, dtype=bool)

    # Build account lookup
    account_by_number = {a.account_number: a for a in accounts}

    for i, txn in enumerate(transactions):
        account_number = _match_transaction(txn)
        if account_number and account_number in account_by_number:
            account = account_by_number[account_number]
            results[i] = TierResult(
                account_number=account_number,
                account_id=str(account.account_id),
                confidence=0.95,
                tier="pattern",
            )
            classified[i] = True

    return BatchTierResult(results=results, classified_mask=classified)


def _match_transaction(txn: TransactionInput) -> str | None:
    """Try to match a single transaction."""
    # Try merchant match first
    if txn.counterparty_name:
        merchant = normalize_merchant(txn.counterparty_name)
        if merchant and merchant in KNOWN_MERCHANTS:
            return KNOWN_MERCHANTS[merchant]

    # Try keyword match in purpose
    purpose_lower = txn.purpose.lower()
    for keyword, account_number in KEYWORDS.items():
        if keyword in purpose_lower:
            return account_number

    return None


def extract_merchants(
    transactions: list[TransactionInput],
) -> list[str | None]:
    """Extract normalized merchant names from transactions."""
    return [
        normalize_merchant(txn.counterparty_name) if txn.counterparty_name else None
        for txn in transactions
    ]
