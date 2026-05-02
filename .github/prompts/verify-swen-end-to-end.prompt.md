---
agent: agent
description: Full end-to-end setup and verification of swen — imports all configured banks, checks DB integrity, direction policy, balance reconciliation, and ML classification quality.
---

# swen end-to-end verification

This prompt sets up a clean swen instance from scratch using all
configured bank credentials, imports 365 days of transactions from
every bank, then performs a comprehensive health check of the resulting
database.

## Pre-conditions

- Docker is running with `swen-postgres` healthy (`docker ps`).
- Local processes for `services/backend` (port 8000) and `services/ml`
  (port 8001) are running with `--reload`. If not, start them per
  [docs/contributing/setup.md](../../docs/contributing/setup.md) and
  verify:
  ```bash
  curl -s http://127.0.0.1:8000/health
  curl -s http://127.0.0.1:8001/health
  ```
- A `.env` file exists at the repo root. **Never paste its contents
  into chat or files — always read values from it at runtime.**

## Step 1 — Reset databases

> Destructive. Confirm with the user before proceeding.

```bash
make db-reset-force
```

Then restart both services so they recreate their schemas via
`Base.metadata.create_all` and reload the latest code. Re-verify
health after restart.

## Step 2 — Register test user

```
POST /api/v1/auth/register
{"email": "test@example.com", "password": "password123"}
```

Capture the `access_token` and use it as `Authorization: Bearer <token>`
for all subsequent calls.

## Step 3 — Configure Geldstrom gateway

Read `GATEWAY_API_KEY` from `.env`.

```
PUT /api/v1/admin/fints_provider/geldstrom-api
{"api_key": "<GATEWAY_API_KEY>", "endpoint_url": "https://geldstrom-api.de"}
```

Requires admin access (the first registered user is admin).

Then activate the provider (without this, all credential POSTs and syncs will fail silently):

```
POST /api/v1/admin/fints_provider/activate
{"mode": "api"}
```

## Step 4 — Add bank credentials for every configured bank

Parse `.env` for **all** FinTS credential blocks — both commented-out
and active lines. A block is a group of `FINTS_*` variables that share
the same index/prefix. For each distinct bank found, POST its
credentials:

```
POST /api/v1/credentials
{
  "blz":        "<FINTS_BLZ>",
  "username":   "<FINTS_USER>",
  "pin":        "<FINTS_PIN>",
  "tan_method": "<FINTS_TAN_METHOD>",
  "tan_medium": "<FINTS_TAN_MEDIUM>"   // omit if empty
}
```

At the time of writing `.env` contains two banks:
- **DKB** (BLZ `12030000`) — active block
- **Atruvia/VR Bank** (BLZ `50031000`) — commented-out block

Add both. If a commented-out block is missing a required field, skip
it and note the omission in the report.

After storing each set of credentials, call the setup endpoint to discover
and link the bank accounts for that BLZ. Capture the returned account IDs
for reference:

```
POST /api/v1/credentials/{blz}/setup
```

Do this for every BLZ that was successfully stored. If the call requires
TAN approval, follow the TAN challenge flow before proceeding.

## Step 4b — Initialise chart of accounts

> **Must run before the first sync.** Without default accounts the import
> will fail for every transaction with `Default expense account (4900) not
> found` / `Default income account (3100) not found`.

```
POST /api/v1/accounts/init-chart
{}
```

Expected response: `accounts_created > 0`, `skipped = false`. If
`skipped = true` the chart was already present (OK — continue).

## Step 5 — Import 365 days of transactions from all banks

```
POST /api/v1/sync/run
{"days": 365}
```

This syncs every linked bank account. Wait for the response (may take
several minutes; the endpoint is synchronous). If the endpoint times
out, poll `GET /api/v1/sync/recommendations` until
`last_successful_sync_date` is recent for all accounts.

## Step 6 — Database health checks

Connect to the `swen` database:
```bash
docker exec -i swen-postgres psql -U postgres -d swen
```

Run all checks below and record the result of each.

### 6a — Import completeness

```sql
-- Total bank transactions vs successfully imported accounting transactions
SELECT
    (SELECT COUNT(*) FROM bank_transactions)          AS bank_txns,
    (SELECT COUNT(*) FROM transaction_imports
     WHERE status = 'success')                        AS imported_ok,
    (SELECT COUNT(*) FROM transaction_imports
     WHERE status = 'failed')                         AS import_failed,
    (SELECT COUNT(*) FROM transaction_imports
     WHERE status = 'skipped')                        AS import_skipped;
```

Expected: `import_failed` = 0, `imported_ok` + `import_skipped` =
`bank_txns`. Note any failures with their `error_message`.

```sql
-- Sample failed imports (if any)
SELECT ti.id, bt.booking_date, bt.amount, bt.purpose, ti.error_message
FROM transaction_imports ti
JOIN bank_transactions bt ON bt.id = ti.bank_transaction_id
WHERE ti.status = 'failed'
ORDER BY bt.booking_date DESC
LIMIT 20;
```

### 6b — Direction-policy violations

Both queries must return **0**:

```sql
-- Debit posted to an income account (money out → income is wrong)
SELECT COUNT(*) AS debit_on_income
FROM journal_entries je
JOIN accounting_accounts a ON a.id = je.account_id
WHERE a.account_type = 'income' AND je.debit_amount > 0;

-- Credit posted to an expense account (money in → expense is wrong)
SELECT COUNT(*) AS credit_on_expense
FROM journal_entries je
JOIN accounting_accounts a ON a.id = je.account_id
WHERE a.account_type = 'expense' AND je.credit_amount > 0;
```

Any non-zero result is a **critical failure** — it means both the ML
direction filter and the backend safety net failed simultaneously.

### 6c — Bank balance reconciliation

The bank-reported balance must match the double-entry net for every
asset account. The two `balance` columns must be equal for every row:

```sql
SELECT
    a.account_number,
    a.name,
    ba.balance                              AS bank_reported,
    ba.balance_date::date                   AS as_of,
    SUM(je.debit_amount - je.credit_amount) AS double_entry_net,
    ba.balance - SUM(je.debit_amount - je.credit_amount) AS delta
FROM accounting_accounts a
JOIN bank_accounts ba ON ba.iban = a.iban
JOIN journal_entries je ON je.account_id = a.id
WHERE a.account_type = 'asset'
GROUP BY a.id, a.account_number, a.name, ba.balance, ba.balance_date
ORDER BY ABS(ba.balance - SUM(je.debit_amount - je.credit_amount)) DESC;
```

A non-zero `delta` indicates missing or duplicate transactions.
Investigate with:

```sql
-- Check for duplicate bank transactions
SELECT bt.booking_date::date, bt.amount, bt.purpose, COUNT(*) AS n
FROM bank_transactions bt
GROUP BY bt.booking_date, bt.amount, bt.purpose
HAVING COUNT(*) > 1
ORDER BY n DESC
LIMIT 20;
```

### 6d — Counter-account classification quality

Show the top 20 counter-accounts and a random sample per account.
Then form your own opinion on whether the classification looks
reasonable given the transaction descriptions:

```sql
-- Top 20 counter-accounts by volume
SELECT
    a.account_number,
    a.name,
    a.account_type,
    COUNT(*) AS txn_count,
    SUM(je.debit_amount + je.credit_amount) AS total_volume
FROM accounting_accounts a
JOIN journal_entries je ON je.account_id = a.id
WHERE a.account_type IN ('expense', 'income')
GROUP BY a.id, a.account_number, a.name, a.account_type
ORDER BY txn_count DESC
LIMIT 20;

-- Sample 5 transactions per top counter-account for plausibility check
SELECT
    a.account_number,
    a.name                         AS counter_account,
    t.date::date,
    t.counterparty,
    LEFT(t.description, 80)        AS purpose,
    je.debit_amount,
    je.credit_amount
FROM accounting_accounts a
JOIN journal_entries je ON je.account_id = a.id
JOIN accounting_transactions t ON t.id = je.transaction_id
WHERE a.account_type IN ('expense', 'income')
  AND a.account_number IN (
      SELECT account_number FROM (
          SELECT a2.account_number, COUNT(*) AS n
          FROM accounting_accounts a2
          JOIN journal_entries je2 ON je2.account_id = a2.id
          WHERE a2.account_type IN ('expense', 'income')
          GROUP BY a2.account_number
          ORDER BY n DESC LIMIT 8
      ) top
  )
ORDER BY a.account_number, t.date DESC;
```

For each top account, comment whether the transactions make sense
(e.g. `4200 Lebensmittel` should contain supermarket purchases,
`3000 Gehalt & Lohn` salary credits, `4900 Sonstiges` only genuinely
uncategorisable items).

### 6e — ML direction-filter smoke test

Directly call the ML service to confirm it cannot propose a
wrong-direction account, independent of the backend safety net:

```bash
curl -s -X POST http://127.0.0.1:8001/classify/batch \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "<USER_UUID>",
    "transactions": [
      {
        "transaction_id": "11111111-1111-1111-1111-111111111111",
        "booking_date": "2025-01-15",
        "purpose": "Habenzins Solidaritätszuschlag Kapitalertragsteuer",
        "amount": "-3.50"
      },
      {
        "transaction_id": "22222222-2222-2222-2222-222222222222",
        "booking_date": "2025-01-15",
        "counterparty_name": "ACME GMBH",
        "purpose": "Gehalt Januar 2025 Lohn",
        "amount": "3500.00"
      }
    ]
  }' | python3 -m json.tool
```

Substitute `<USER_UUID>` with the UUID from Step 2. Then cross-check
the returned `account_id` values:

```sql
SELECT account_number, name, account_type
FROM accounting_accounts
WHERE id IN ('<account_id_1>', '<account_id_2>');
```

Required:
- The `-3.50` debit → `account_type = expense`
- The `+3500.00` credit → `account_type = income`

## Reporting

Produce a table with one row per check:

| Check | Query / endpoint | Result | Pass? |
|---|---|---|---|
| Services healthy | GET /health | … | ✅/❌ |
| Import completeness | SQL 6a | X ok, Y failed | ✅/❌ |
| Direction violations | SQL 6b | 0 / 0 | ✅/❌ |
| Balance reconciliation | SQL 6c | delta = 0 for all | ✅/❌ |
| Classification quality | SQL 6d | subjective assessment | ✅/⚠️/❌ |
| ML direction filter | curl + SQL 6e | expense / income | ✅/❌ |

Flag any ❌ with the raw query output and your diagnosis.
