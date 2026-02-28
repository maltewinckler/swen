# Concepts

This section explains the domain knowledge that helps you use SWEN effectively. You do not need to be an accountant — but understanding a few core ideas will make the UI much less surprising.

<div class="grid cards" markdown>

-   :ledger: **[Double-Entry Bookkeeping](double-entry.md)**

    Why SWEN uses double-entry, what debits and credits mean, and how a bank import turns into journal entries.

-   :books: **[Domain Model](domain-model.md)**

    The precise vocabulary used throughout SWEN: what a `Transaction` is, how it differs from a `BankTransaction`, and why there is both an `Account` and a `BankAccount`.

-   :arrows_counterclockwise: **[Transaction Deduplication](deduplication.md)**

    Why bank APIs return the same transaction multiple times, and how SWEN's hash + sequence approach handles it correctly.

</div>

## What SWEN Is (and Is Not)

**SWEN is:**

- A **personal bookkeeping tool** — you record where your money comes from and goes to
- A **bank sync client** — it fetches raw transactions from your bank via FinTS
- An **AI assistant** — it suggests counter-accounts so you do not have to categorise manually

**SWEN is not:**

- A budget planner or goal tracker (no envelope budgeting, no "savings goals")
- A multi-currency app (EUR only)
- A tax preparation tool (no DATEV export, no VAT handling)
- A replacement for GnuCash or Actual Budget for complex accounting needs
