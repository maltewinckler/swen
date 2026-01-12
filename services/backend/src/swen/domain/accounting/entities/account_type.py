"""Account type enumeration for double-entry bookkeeping."""

from enum import Enum


class AccountType(Enum):
    """Types of accounts in double-entry bookkeeping."""

    ASSET = "asset"  # Bank accounts, cash, investments
    LIABILITY = "liability"  # Credit cards, loans
    EQUITY = "equity"  # Opening balances, retained earnings
    INCOME = "income"  # Salary, dividends
    EXPENSE = "expense"  # Groceries, rent, etc.

    def is_debit_normal(self) -> bool:
        return self in (AccountType.ASSET, AccountType.EXPENSE)
