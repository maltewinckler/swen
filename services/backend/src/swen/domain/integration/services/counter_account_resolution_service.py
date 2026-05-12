"""Counter-account resolution service.

Domain service for validating and applying counter-account proposals.

Responsibilities:
1. Validating that a counter-account proposal respects account direction rules
2. Utility functions for querying current transaction counter-accounts
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from swen.domain.accounting.entities import Account
from swen.domain.accounting.services.classification_rules import ClassificationRules
from swen.domain.accounting.well_known_accounts import WellKnownAccounts

if TYPE_CHECKING:
    from swen.domain.accounting.aggregates import Transaction

logger = logging.getLogger(__name__)


class CounterAccountResolutionService:
    """Domain service for validating and applying counter-account proposals.

    All methods are static — no instance state required.
    """

    @staticmethod
    def is_valid_proposal(
        is_money_outflow: bool,
        account: Account,
    ) -> bool:
        """Check if a proposal is valid for the given transaction direction."""
        return ClassificationRules.is_valid_counter_direction(
            is_money_outflow=is_money_outflow,
            account_type=account.account_type,
        )


def get_counter_account(txn: Transaction) -> Account | None:
    """Get the current counter-account (non-protected entry) of a transaction."""
    for entry in txn.entries:
        if not txn.is_entry_protected(entry):
            return entry.account
    return None


def has_fallback_counter_account(txn: Transaction) -> bool:
    """Check if the transaction's counter-account is a fallback account."""
    for entry in txn.entries:
        if (
            not txn.is_entry_protected(entry)
            and entry.account.account_number in WellKnownAccounts.FALLBACK_ACCOUNTS
        ):
            return True
    return False


def _is_money_outflow(txn: Transaction) -> bool:
    """Determine if a bank-import transaction represents money leaving.

    For bank imports, the protected entry is the asset entry.
    - Asset entry is CREDIT → money OUT (outflow)
    - Asset entry is DEBIT → money IN (inflow)
    """
    for entry in txn.entries:
        if txn.is_entry_protected(entry):
            return not entry.is_debit()  # Credit on asset = outflow
    # Fallback: treat as outflow (safer default for expenses)
    return True


def _counter_entry_is_debit(txn: Transaction) -> bool:
    """Determine if the counter-entry should be a debit or credit.

    The counter-entry is the opposite of the protected (asset) entry.
    """
    for entry in txn.entries:
        if txn.is_entry_protected(entry):
            return not entry.is_debit()
    return True
