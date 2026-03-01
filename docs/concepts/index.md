# Concepts

This section explains the domain knowledge that helps you use SWEN effectively. You do not need to be an accountant but understanding a few core ideas will make the UI and data flows more natural.

<div class="grid cards" markdown>

-   :ledger: **[Double-Entry Bookkeeping](double-entry.md)**

    Why SWEN uses double-entry, what debits and credits mean, and how a bank import turns into journal entries.

-   :bank: **[FinTS/HBCI Integration](fints.md)**

    What this protocol is, what bureaucracy is involved, and what is necessary to enable it for your bank.

-   :books: **[Domain Model](domain-model.md)**

    The precise vocabulary used throughout SWEN: what a `Transaction` is, how it differs from a `BankTransaction`, and why there is both an `Account` and a `BankAccount`.

-   :arrows_counterclockwise: **[Transaction Deduplication](deduplication.md)**

    Why bank APIs return the same transaction multiple times, and how SWEN's hash + sequence approach handles it correctly.

</div>
