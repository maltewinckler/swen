"""Domain service for ML classification business rules.

This service owns the accounting rules that govern whether an
ML-suggested counter-account is valid for a given transaction direction.

It is a pure domain service with no infrastructure dependencies.
"""

from __future__ import annotations

from swen.domain.accounting.entities.account_type import AccountType


class ClassificationRules:
    """Business rules for ML-based counter-account classification.

    Enforces double-entry accounting constraints:
    - Money OUT (debit on bank, amount < 0): counter-account must be
      EXPENSE or LIABILITY. An INCOME counter-account would merely
      reduce income — wrong.
    - Money IN (credit on bank, amount > 0): counter-account must be
      INCOME or EQUITY. An EXPENSE counter-account would merely
      reduce an expense — wrong.
    """

    @staticmethod
    def is_valid_counter_direction(
        is_money_outflow: bool,
        account_type: AccountType,
    ) -> bool:
        """Check if the account type is valid for the transaction direction.

        Parameters
        ----------
        is_money_outflow
            True if money is leaving the bank account (debit on bank /
            amount < 0 in BankTransaction / credit on asset entry).
        account_type
            The type of the ML-suggested counter-account.

        Returns
        -------
        bool
            True if the direction is valid, False if it violates
            double-entry rules.
        """
        if is_money_outflow and account_type == AccountType.INCOME:
            return False
        if not is_money_outflow and account_type == AccountType.EXPENSE:
            return False
        return True
