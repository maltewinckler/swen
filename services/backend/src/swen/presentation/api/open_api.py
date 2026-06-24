"""OpenAPI configuration for the SWEN API.

This module centralizes OpenAPI tags metadata for Swagger UI documentation.
Import OPENAPI_TAGS in app.py instead of defining it inline.
"""

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "Authentication",
        "description": """User authentication and session management.

**Registration & Login:**
- Register new accounts with email/password
- Login to obtain JWT tokens
- Refresh tokens before expiry

**Security:**
- Passwords are securely hashed (bcrypt)
- JWT tokens for stateless authentication
- Account lockout after failed attempts
""",
    },
    {
        "name": "Admin",
        "description": """Administrative user and bank configuration management.

**User Management:**
- List, create, delete users
- Update user roles (admin/user)

**FinTS Configuration:**
- Manage bank product IDs and institute CSV files
- Configure FinTS provider settings
""",
    },
    {
        "name": "Accounts",
        "description": """Chart of accounts management (double-entry bookkeeping).

**Account Types:**
- `asset`: Bank accounts, cash, receivables (normal debit balance)
- `liability`: Credit cards, loans, payables (normal credit balance)
- `equity`: Owner's equity, retained earnings
- `income`: Salary, interest, dividends (credit increases)
- `expense`: Groceries, rent, utilities (debit increases)

**Bank Accounts:**
- Automatically created when syncing with banks
- Mapped by IBAN for transaction import
""",
    },
    {
        "name": "Banking",
        "description": """Bank account and credential management.

**Credentials:**
- Store bank login credentials (encrypted at rest)
- Manage TAN methods and mediums
- Lookup bank info by BLZ

**Bank Accounts:**
- Import bank accounts from FinTS connections
- View imported account list
""",
    },
    {
        "name": "Transactions",
        "description": """Transaction management and double-entry journal.

**Transaction States:**
- `draft`: Imported but not finalized, can be edited
- `posted`: Finalized, affects account balances

**Features:**
- Automatic internal transfer detection between your accounts
- Double-entry bookkeeping (every transaction has balanced debits/credits)
- Filter by date range, account, or status
""",
    },
    {
        "name": "Dashboard",
        "description": """Financial summaries for quick overview.

**Available Data:**
- Income/expense totals for any period
- Current account balances
- Spending breakdown by category (expense accounts)
- Recent transactions

**Time Periods:**
- Specify `days` to look back from today
- Or specify `month` in YYYY-MM format
- Defaults to current month
""",
    },
    {
        "name": "Analytics",
        "description": """Financial analytics for charts and visualizations.

**Time Series Data (for line/bar charts):**
- `/spending/over-time` - Monthly spending by category
- `/income/over-time` - Monthly income totals
- `/net-income/over-time` - Monthly savings (income - expenses)

**Breakdown Data (for pie charts):**
- `/spending/breakdown` - Spending distribution by category

**Chart Types Supported:**
- Line charts (income trends, savings)
- Stacked bar charts (spending by category)
- Pie/donut charts (spending breakdown)
- Multi-line charts (category comparison)
""",
    },
    {
        "name": "Sync",
        "description": """Bank transaction synchronization via FinTS.

**How it works:**
1. Connects to your bank using stored credentials
2. Fetches transactions for the specified date range
3. Imports new transactions (skips duplicates)
4. Detects internal transfers between your accounts

**TAN Handling:**
- **Decoupled TAN** (SecureGo plus, pushTAN): API waits up to 5 minutes for approval
- **Interactive TAN** (photoTAN, chipTAN): Use CLI instead

**Important:** Set HTTP client timeout to 6+ minutes for TAN-requiring operations.
""",
    },
    {
        "name": "Integration",
        "description": """Account mapping and import orchestration.

**Mappings:**
- View bank account to ledger account mappings
- Manage IBAN-to-account links

**Imports:**
- Track import history and statistics
- Monitor import health and failures
""",
    },
    {
        "name": "Exports",
        "description": """Data export for backup and analysis.

**Export Types:**
- `/exports/transactions` - Export transaction history
- `/exports/accounts` - Export chart of accounts
- `/exports/full` - Full backup (transactions + accounts + mappings)

**Filters:**
- Filter by days (history range)
- Filter by status (posted/draft)
- Filter by account type or IBAN

**Use Cases:**
- Spreadsheet analysis
- Data backup before migrations
- Reporting
""",
    },
    {
        "name": "Preferences",
        "description": """User preference management.

**Sync Settings:**
- `auto_post_transactions` - Auto-finalize imported transactions

**Display Settings:**
- `default_currency` - Default currency (EUR, USD, etc.)
- `show_draft_transactions` - Include drafts in lists
- `default_date_range_days` - Default filter range
""",
    },
    {
        "name": "Onboarding",
        "description": """New user onboarding and setup status.

**Onboarding Flow:**
1. Initialize expense accounts (templates)
2. Connect first bank
3. Add more banks (optional)
4. Add manual accounts (optional)

**Status is derived from existing data:**
- `accounts_initialized` - True if expense accounts exist
- `first_bank_connected` - True if bank credentials exist
- `has_transactions` - True if transactions exist
""",
    },
    {
        "name": "Health",
        "description": "Service health monitoring endpoints.",
    },
    {
        "name": "Info",
        "description": "API information and discovery.",
    },
]
