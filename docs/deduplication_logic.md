# Bank Transaction Deduplication Logic

This document explains why SWEN uses a hash + sequence deduplication strategy, and why simpler approaches fail. I have encountered this problem in all other bookkeeping variants I have tested that had automatic sync.

## The Core Problem

When syncing transactions from banks via FinTS/HBCI: **Banks do not provide globally unique, stable transaction identifiers.**

This means we cannot simply "check if this ID exists" before inserting. We must derive uniqueness from the transaction content itself.

## Why Naive Deduplication Fails

**The idea**: Create a hash of all transaction fields. If the hash exists, it's a duplicate. This fails in the case of same vendor, same amount, same reference, e.g. you buy a drink at a store. Later that day you buy the same drink at the same store again. The bank will return this information

```
Transaction 1:  2024-01-20  DE1234...   €1.20  "Visa Debitumsatz"
Transaction 2:  2024-01-20  DE1234...   €1.20  "Visa Debitumsatz"
```

**Result**: Both transactions compute the same hash which means, you will loose one actual transaction and your accounts are out of balance.

## The Solution: Hash + Sequence

We need to handle both:
1. **Detecting duplicates** when re-syncing the same transactions
2. **Preserving multiples** when identical transactions legitimately exist


### HThe Deduplication Strategy

When processing a batch of transactions from the bankwe assign an in-batch sequence number that counts the occurrences of the same hash within the imported batch.

```
Bank returns these transactions (in order):

  [1] €-50.00  "Netflix"     -> hash=abc    : 1st with this hash -> seq=1
  [2] €=1.20   "Visa Debit"  -> hash=xyz    : 1st with this hash -> seq=1
  [3] €-1.20   "Visa Debit"  -> hash=xyz    : 2nd with this hash -> seq=2
  [4] €-1.20   "Visa Debit"  -> hash=xyz    : 3rd with this hash -> seq=3
  [5] €100.00  "Salary"      -> hash=def    : 1st with this hash -> seq=1
```

Now, before inserting into the bank-transaction-database, we query whether these (hash, sequence) pairs already exist in the database. If it does, we skip, else we add. This guarantees no data loss and no duplicates. This assumes that we always sync full historical days (not splitting the days at noon which might yield edge cases). Moreover, banks generally give data ordered by time. Even if this would not be the case, we would not create any duplicates or lose data.

We still assign random UUIDs (uuid4) to transactions which are persisted in the database. A deterministic ID bsaed on data and sequence number would make the implementation of the logic more complex because we would have to query the database for how many ids with this data exist to do the comparison.
