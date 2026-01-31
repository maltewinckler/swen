class WellKnownAccounts:
    """Standard account numbers with special system meaning."""

    # Equity account used for opening balance entries
    OPENING_BALANCE_EQUITY = "2000"

    FALLBACK_EXPENSE = "4900"  # Sonstiges (expense fallback)
    FALLBACK_INCOME = "3100"  # Sonstige Einnahmen (income fallback)

    # Set of all fallback account numbers (for filtering)
    FALLBACK_ACCOUNTS = frozenset({FALLBACK_EXPENSE, FALLBACK_INCOME})
