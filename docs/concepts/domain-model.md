# Domain Model

SWEN uses a precise vocabulary throughout the codebase, API, and UI. This page is the **ubiquitous language reference** — if you see a term in the code or a UI label you don't recognise, look it up here.

## Banking Domain

These concepts come directly from the FinTS banking world.

### BankAccount

A real-world bank account identified by an **IBAN**. Corresponds to a single account at a single bank. Each `BankAccount` in SWEN is linked to a bookkeeping `Account` (of type Asset) that records its running balance.

**Key fields:** `iban`, `bic`, `account_name`, `bank_name`, `linked_account_id`

### BankTransaction

A raw transaction record fetched from the bank via FinTS. Represents a **bank statement line** — not yet interpreted in bookkeeping terms.

**Key fields:** `bank_account_id`, `amount`, `value_date`, `booking_date`, `purpose`, `counterparty_name`, `counterparty_iban`, `transaction_hash`

A `BankTransaction` is **not** a double-entry record. It becomes one when SWEN creates a linked `Transaction` (Draft or Posted).

### Counterparty

The other party in a bank transfer. Identified by `name` and optionally by `iban`. Counterparties are extracted from `BankTransaction.purpose` and `BankTransaction.counterparty_name` fields.

### Purpose

The free-text reference field of a bank transaction (`Verwendungszweck` in German). This is what you type when you make a bank transfer. SWEN's ML classification reads this field heavily.

---

## Accounting Domain

These concepts come from double-entry bookkeeping.

### Account

A bookkeeping **ledger account**. Not a bank account — see above. Has a **type** (Asset, Liability, Equity, Income, Expense) and a name (e.g. "Groceries", "Salary").

Accounts form a **tree** (chart of accounts). Each leaf account accumulates a running balance.

**Key fields:** `name`, `account_type`, `parent_id`, `is_system`

### Transaction *(bookkeeping)*

A double-entry transaction consisting of two or more `JournalEntry` lines that sum to zero. Linked to a `BankTransaction` when created from a bank import.

!!! warning "Naming collision"
    The word "transaction" is overloaded. In SWEN code and docs:
    - `Transaction` (capital T, in the accounting domain) = journal entry
    - `BankTransaction` = raw bank statement line
    - In the UI, "transaction" usually means the `BankTransaction` + its linked `Transaction` together

**States:** `DRAFT` → `POSTED`

### JournalEntry

A single line in a `Transaction`. Specifies an `Account`, an `amount`, and a `side` (debit or credit). A valid Transaction always has at least two JournalEntries with equal debit and credit totals.

### Counter-Account

The bookkeeping account that "receives" the other side of a bank import. For a supermarket payment, the bank Asset account is debited and the Groceries Expense account (the counter-account) is credited. SWEN's ML pipeline predicts the counter-account automatically.

---

## Integration Domain

These concepts describe how banking and accounting are connected.

### AccountMapping

A persistent rule that maps a `BankAccount` to its corresponding bookkeeping `Account`. Created during the bank account onboarding wizard. Required before any imports can run.

### InternalTransfer

A bank transfer between **two of your own accounts** (e.g. moving savings). SWEN detects these heuristically by matching counterparty IBANs against your known `BankAccount` list and creates a single balanced `Transaction` spanning both accounts.

### Import

A single execution of the bank sync process for one `BankAccount`. Fetches `BankTransaction` records, deduplicates them, runs ML classification, and creates Draft `Transaction` records.

---

## Terms SWEN Intentionally Avoids

| Avoid | Use instead | Reason |
|---|---|---|
| "Category" | `Account` (Expense/Income) | "Category" implies a tag, not a ledger position |
| "Wallet" | `BankAccount` or `Account` | Ambiguous |
| "Entry" alone | `JournalEntry` or `Transaction` | Disambiguates the two levels |
| "Sync" for accounting | "Post" or "Import" | "Sync" is reserved for bank fetch operations |
