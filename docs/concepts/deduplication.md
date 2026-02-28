# Transaction Deduplication

When SWEN imports bank transactions, it must avoid creating duplicates. This page explains why the problem is harder than it looks and how SWEN solves it.

## Why Bank Transaction IDs Are Unreliable

FinTS returns a `transaction_id` field for each statement line, but:

- Many German banks do **not** set it (the field is optional in the spec)
- Some banks reuse IDs across date ranges
- Some banks assign new IDs to the same transaction on re-download

You cannot rely on `transaction_id` as a stable primary key.

## The Hash + Sequence Approach

SWEN generates a deterministic **content hash** for each `BankTransaction` from a combination of:

```
hash = SHA-256(
    bank_account_id,
    booking_date,
    value_date,
    amount_cents,
    counterparty_iban,    # may be empty
    counterparty_name,    # may be empty
    purpose[:200]         # trimmed — some banks truncate differently
)
```

If a transaction with the same hash already exists, the new record is considered a duplicate and discarded.

### The Sequence Field

When two transactions on the **same day** have identical amounts and counterparties (e.g. two €50 ATM withdrawals on the same day), their hashes collide. SWEN breaks the tie with a **sequence number** appended to the hash:

```
hash + "_0"   ← first occurrence
hash + "_1"   ← second occurrence
```

A full-day sync is required to reliably reconstruct the correct sequence for a given day.

## Why Full-Day Syncs Are Required

SWEN always fetches **complete days** from the bank, even if you are only interested in "new" transactions. This is necessary because:

1. Banks may deliver transactions in a different order on different calls
2. A partial sync (e.g. "last 3 transactions") cannot reconstruct the correct sequence number for same-day duplicates
3. Reversals and corrections sometimes arrive with the same booking date as the original

SWEN fetches from `max(last_import_date - 1 day, account_open_date)` to account for late-arriving corrections.

## Idempotency

Importing the same date range twice is safe. On the second call:

- Existing transactions are identified by hash (+ sequence) and skipped
- Only genuinely new transactions are inserted
- No existing `BankTransaction` or `Transaction` record is modified

## Edge Cases

### Same-Day Same-Amount Transfers

Two identical ATM withdrawals on the same day → sequence `_0` and `_1`. If the bank only returns one on a re-import, SWEN discards it correctly (hash `_0` already exists).

### Bank Sends Partial Days

Some banks deliver transactions up to noon on the current day mid-day. SWEN treats "today" as in-progress and always re-fetches the current day on the next sync.

### Pending vs Booked

FinTS distinguishes "pending" (not yet booked) from "booked" transactions. SWEN currently imports only **booked** transactions. Pending transactions are ignored.

### Reversal Transactions

A bank reversal often appears as a new `BankTransaction` with the opposite amount and the same purpose. SWEN does **not** automatically cancel the original — it appears as a new Draft transaction for you to review and post.
