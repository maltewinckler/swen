"""Fallback tier for unclassified transactions."""


from swen_ml_contracts import AccountOption, TransactionInput

from swen_ml.pipeline.tiers.base import TierResult

# Default fallback accounts
FALLBACK_EXPENSE = "4900"  # Sonstiges
FALLBACK_INCOME = "3100"  # Sonstige Einnahmen


def fallback_single(
    txn: TransactionInput,
    accounts: list[AccountOption],
) -> TierResult:
    """Assign fallback account based on transaction sign."""
    account_number = FALLBACK_EXPENSE if txn.amount < 0 else FALLBACK_INCOME

    # Find matching account
    account = next(
        (a for a in accounts if a.account_number == account_number),
        accounts[0],  # Use first account as last resort
    )

    return TierResult(
        account_number=account.account_number,
        account_id=str(account.account_id),
        confidence=0.0,
        tier="fallback",
    )
