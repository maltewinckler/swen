# SWEN Ubiquitous Language

This document defines the **ubiquitous language** for SWEN. All members, code, documentation, and user interfaces should use these terms consistently. Ubiquitous Language is a concept from Domain-Driven Design and describes a shared vocabulary between developers and domain experts, used consistently in code, conversations, and documentation.

---

## Table of Contents

1. [Banking Domain](#1-banking-domain)
2. [Accounting Domain](#2-accounting-domain)
3. [Integration Domain](#3-integration-domain)
7. [Terms to Avoid](#4-terms-to-avoid)

## 1. Banking Domain

The banking domain represents the **external world**: how banks see and report your financial activity.

### Bank Account

**Definition**: An actual account you own at a financial institution.


- **IBAN**: Unique identifier (International Bank Account Number)
- **BLZ**: German bank code (Bankleitzahl), embedded in IBAN
- **Account Holder**: Name of the person/entity owning the account
- **Balance**: Current amount of money in the account

**In Code**: `BankAccount` value object in banking domain

### Bank Transaction

**Definition**: A single movement of money as reported by the bank. This is raw data from the bank before it is processed into our accounting system.

- **Booking Date**: When the bank recorded the transaction
- **Value Date**: When the money actually moved (for interest calculation)
- **Amount**: Positive (credit/incoming) or negative (debit/outgoing)
- **Currency**: Usually EUR
- **Purpose**: Bank-provided description text
- **Counterparty**: The other party (see below)

**In Code**: `BankTransaction` value object in banking domain

### Counterparty

**Definition**: The external party on the other side of a Bank Transaction — the merchant, company, or person you transacted with.

- **Name**: Human-readable name (e.g., "REWE Markt GmbH")
- **IBAN**: Bank account of the counterparty (if available)

**Why this term?**
- Neutral: works for both payer and payee
- Standard financial terminology
- Single term for both income and expense scenarios

**Examples**:
- "REWE Markt GmbH" (grocery store)
- "Max Mustermann" (person sending you money)
- "Netflix International" (subscription service)

**In Code**: `applicant_name` and `applicant_iban` in `BankTransaction`; stored as `counterparty` metadata in `Transaction`. The field `applicant_iban` is not necessarily unique because many banks use *swamp* ibans for Visa Debitcard transactions.

### Purpose

**Definition**: The bank-provided text describing what the Bank Transaction is for. Often contains reference numbers, mandate IDs, or free-text descriptions.

**Examples**:
- "Visa Debitkartenumsatz"
- "Dauerauftrag Miete November"
- "SEPA Lastschrift Mandate-ID: ABC123"

Purpose is raw bank data. We transform this into a cleaner **Description** when creating Transactions.

## 2. Accounting Domain

The accounting domain represents **your personal bookkeeping system** using double-entry bookkeeping principles.

### Account

**Definition**: A bookkeeping account in your chart of accounts. NOT a bank account — this is an accounting concept.

- **Account Number**: Unique identifier (e.g., "4100", "DE1234949858858")
- **Name**: Human-readable name
- **Account Type**: One of: Asset, Liability, Equity, Income, Expense
- **Currency**: Default currency for the account

**Account Types**:

- **Asset** (Normal Balance: Debit): Things you own — Bank accounts, cash
- **Liability** (Normal Balance: Credit): Things you owe — Credit cards, loans
- **Equity** (Normal Balance: Credit): Net worth, retained earnings — Opening balance
- **Income** (Normal Balance: Credit): Money earned — Salary, dividends, interest
- **Expense** (Normal Balance: Debit): Money spent — Groceries, rent, utilities

**In Code**: `Account` entity in accounting domain.

#### Asset Account

**Definition**: An Account of type Asset. Represents something you own that has monetary value.

In SWEN, each **Bank Account** is linked to an **Asset Account** for bookkeeping purposes.

**Examples**:
- "ING - Girokonto" (linked to IBAN DE26...)
- "Bargeld" (physical cash)
- "Depot" (investment account)

#### Expense Account

**Definition**: An Account of type Expense. Represents a category of spending.

**Examples**:
- "Lebensmittel (Groceries)" - Account 4000
- "Restaurant & Café" - Account 4100
- "Transport" - Account 4300
- "Sonstiges (Other)" - Account 4900

#### Income Account

**Definition**: An Account of type Income. Represents a source of earnings.

**Examples**:
- "Gehalt (Salary)" - Account 3000
- "Sonstige Einnahmen (Other Income)" - Account 3100

### Transaction

**Definition**: A complete, balanced double-entry booking. Every Transaction has at least two Journal Entries where total debits equal total credits.

- **Date**: When the transaction occurred
- **Description**: Human-readable summary of the transaction
- **Counterparty**: The external party involved (from banking data)
- **Entries**: List of Journal Entries (debits and credits)
- **Is Posted**: Whether the transaction is finalized
- **Metadata**: Additional data (tags, original purpose, etc.)

**States**:
- **Draft**: Created but not finalized, can be edited
- **Posted**: Finalized, affects account balances

**Transaction Types**
- **Expense Transaction**: Money going out to pay for something.
- **Income Transaction**: Money coming in from earnings.
- **Internal Transfer**: Money moving between your own accounts.

**In Code**: `Transaction` aggregate root in accounting domain

### Journal Entry

**Definition**: A single line within a Transaction which represents either a debit or a credit to one Account.

- **Account**: The Account being debited or credited
- **Debit**: Amount debited (left side of T-account)
- **Credit**: Amount credited (right side of T-account)

**Rules**:
- Each Journal Entry affects exactly one Account
- A Transactions total debits must equal total credits
- Debit increases Asset/Expense accounts
- Credit increases Liability/Equity/Income accounts

**In Code**: `JournalEntry` entity in accounting domain

### Counter-Account

**Definition**: In a simple two-entry Transaction, the Counter-Account is the "other" Account — the one opposite your bank (Asset) account.

- **Expense**: Asset Account credited (money out), Expense Account debited
- **Income**: Asset Account debited (money in), Income Account credited
- **Internal Transfer**: Both are Asset Accounts — one debited, one credited

**Why this term?**
- Standard double-entry bookkeeping terminology
- Clearly indicates the account on the opposite side of the entry
- Works for all transaction types although it sounds a bit clunky

**Example**:
- You buy groceries for €50
- Asset Account "ING Girokonto" is credited €50
- Counter-Account "Lebensmittel" (Expense) is debited €50

**In Code**: Derived from Journal Entries: the entry's account (not bank account!)

### Description

**Definition**: A human-readable summary of what the Transaction is about. Generated from bank data during import.

**Generation Rules**:
1. **Internal Transfer**: "Transfer to {Counter-Account name}" or "Transfer from {Counter-Account name}"
2. **External with Counterparty**: "{Counterparty} - {Purpose}"
3. **External without Counterparty**: "{Purpose}"

**Examples**:
- "Transfer to Volksbank Tagesgeld"
- "REWE Markt - Kartenzahlung"
- "Lastschrift Netflix Abo"


## 3. Integration Domain

The integration domain **bridges** the banking and accounting domains.

### Account Mapping

**Definition**: A configuration that links a Bank Account (IBAN) to an Asset Account in the bookkeeping system.

- **IBAN**: The Bank Account identifier
- **Asset Account ID**: The linked bookkeeping Asset Account
- **Account Name**: Display name for this mapping
- **Is Active**: Whether to import transactions from this account

**Purpose**:
- Enables automatic import of Bank Transactions
- Determines which Asset Account to use for each bank

**Example**:
- IBAN `DE8012345767582999` → Asset Account "ING Girokonto"

**In Code**: `AccountMapping` entity in integration domain

### Internal Transfer

**Definition**: A Transaction that moves money between two of your own Asset Accounts. No income or expense is involved. Your total net worth does not change.

**Characteristics**:
- Both Journal Entries are to Asset Accounts
- One Asset is debited (receives money)
- One Asset is credited (sends money)
- Marked with `is_internal_transfer: true` in metadata
- Detected when Counterparty IBAN exists in Account Mappings

**Example**:
- Transfer €500 from ING Girokonto to Tagesgeld
- Journal Entry 1: Debit "Tagesgeld" €500
- Journal Entry 2: Credit "ING Girokonto" €500

**Why this term?**
- "Internal" emphasizes it's within your own financial ecosystem
- Distinguishes from external transfers (sending to others)
- Clear that no income/expense is recorded

**In Code**: `Transaction.is_internal_transfer` property, `compute_transfer_identity_hash()` for deduplication

### Import

**Definition**: The process of creating accounting Transactions from Bank Transactions.

**Steps**:
1. Fetch Bank Transactions from the bank (via FinTS)
2. For each Bank Transaction:
   - Check for duplicates (idempotency)
   - Detect if Internal Transfer
   - Determine Counter-Account (categorize)
   - Create double-entry Transaction
   - Track import status

**In Code**: `TransactionImportService` in application layer


## 4. Terms to Avoid

These terms are ambiguous or overloaded. Do not use them:

- **"Category"**: Ambiguous — use "Counter-Account" or "Expense Account"
- **"Transfer" (without Prefix)**: Could be internal or external — use "Internal Transfer" or "Bank Transfer"
- **"Booking"**: Vague — use "Transaction" or "Journal Entry"
- **"Entry"**: Ambiguous — use "Transaction" or "Journal Entry"
- **"Category Account"**: Mixing terms — use "Expense Account" or "Income Account"
- **"Payee/Payer"**: Requires knowing direction - use "Counterparty"
