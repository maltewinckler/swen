# Description

When the Girokonto A was synced first (with data starting from 2025-01-20), and then Girokonto B was synced second (with data going back to 2024-01-25), there's a discrepancy of in Girokonto A account balance if Girokonto B transfers money regularly to Girokonto A.

## Root Cause

The problem is in the `TransferReconciliationService.detect_transfer()` method and the subsequent flow in `TransactionImportService`. When processing a Girokonto B transaction from 2024, the system:
* Detects that the counterparty IBAN (Girokonto A) has an account mapping. Thus, marks as internal transfer
* Creates journal entries that debit Girokonto A and credit Girokonto B
But this is incorrect because:
* Girokonto A's opening balance date is 2025-01-20
* Transactions before that date are already "baked into" Girokonto A's opening balance.
* Adding explicit debits to Girokonto A for pre-opening-balance transfers causes double-counting.

## Solution

The fix creates **opening balance adjustments** for pre-opening-balance internal transfers. We did not need to make any changes to our core domain. We just added a service `OpeningBalanceAdjustmentService` and created one more `TransactionSource` for easier filtering.

## How It Works

For an incoming transfer of X EUR to account A that predates A's opening balance:
- The internal transfer creates: Debit A (X), Credit B (X)
- The adjustment creates: Debit Equity (X), Credit A (X)
- Net effect on A: 0 (the money is correctly attributed to the opening balance)
