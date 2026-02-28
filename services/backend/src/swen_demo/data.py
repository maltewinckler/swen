"""Demo data definitions for realistic German personal finance transactions.

AI generated.
This module contains templates for generating realistic transaction data
that resembles typical German household finances.

All data is fictional and used for demonstration purposes only.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class TransactionTemplate:
    """Template for generating a transaction."""

    category_account_number: str  # Maps to expense/income account
    counterparty: str
    description: str
    amount_min: Decimal
    amount_max: Decimal
    counterparty_iban: Optional[str] = None


@dataclass(frozen=True)
class AssetAccountDef:
    """Definition for an asset account."""

    name: str
    account_number: str
    iban: str | None
    opening_balance: Decimal
    description: Optional[str] = None


# =============================================================================
# Asset Accounts (Bank accounts, cash)
# =============================================================================

DEMO_ASSET_ACCOUNTS: list[AssetAccountDef] = [
    AssetAccountDef(
        name="DKB Girokonto",
        account_number="1010",
        iban="DE89370400440532013000",
        opening_balance=Decimal("4850.00"),
        description="Main checking account for daily expenses",
    ),
    AssetAccountDef(
        name="ING Tagesgeldkonto",
        account_number="1100",
        iban="DE91100000000123456789",
        opening_balance=Decimal("2500.00"),
        description="Savings account for emergency fund",
    ),
    AssetAccountDef(
        name="Bargeld",
        account_number="1200",
        iban=None,
        opening_balance=Decimal("120.00"),
        description="Cash on hand",
    ),
]


# =============================================================================
# Income Templates
# =============================================================================

INCOME_TEMPLATES: list[TransactionTemplate] = [
    # Salary (monthly)
    TransactionTemplate(
        category_account_number="3000",  # Gehalt & Lohn
        counterparty="TechCorp GmbH",
        description="Gehalt Januar",  # Will be dynamically updated
        amount_min=Decimal("3200.00"),
        amount_max=Decimal("3200.00"),  # Fixed salary
        counterparty_iban="DE89370400440532013001",
    ),
    # Other income (occasional)
    TransactionTemplate(
        category_account_number="3100",  # Sonstige Einnahmen
        counterparty="PayPal Europe",
        description="Rückerstattung",
        amount_min=Decimal("15.00"),
        amount_max=Decimal("85.00"),
    ),
    TransactionTemplate(
        category_account_number="3100",  # Sonstige Einnahmen
        counterparty="Finanzamt Berlin",
        description="Steuererstattung",
        amount_min=Decimal("250.00"),
        amount_max=Decimal("450.00"),
    ),
]


# =============================================================================
# Expense Templates by Category
# =============================================================================

# Rent (4100) - Monthly
RENT_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4100",
        counterparty="Hausverwaltung Schmidt & Partner",
        description="Miete + Nebenkosten",
        amount_min=Decimal("950.00"),
        amount_max=Decimal("950.00"),  # Fixed rent
        counterparty_iban="DE44500105175407324931",
    ),
]

# Utilities (4110) - Monthly/Quarterly
UTILITIES_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4110",
        counterparty="Vattenfall Europe Sales",
        description="Stromabschlag",
        amount_min=Decimal("65.00"),
        amount_max=Decimal("85.00"),
    ),
    TransactionTemplate(
        category_account_number="4110",
        counterparty="GASAG AG",
        description="Gasabschlag Heizung",
        amount_min=Decimal("45.00"),
        amount_max=Decimal("75.00"),
    ),
    TransactionTemplate(
        category_account_number="4110",
        counterparty="Rundfunk ARD ZDF",
        description="Rundfunkbeitrag",
        amount_min=Decimal("18.36"),
        amount_max=Decimal("18.36"),
    ),
]

# Groceries (4200) - Weekly
GROCERY_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4200",
        counterparty="REWE",
        description="REWE SAGT DANKE",
        amount_min=Decimal("25.00"),
        amount_max=Decimal("85.00"),
    ),
    TransactionTemplate(
        category_account_number="4200",
        counterparty="LIDL",
        description="LIDL SAGT DANKE",
        amount_min=Decimal("18.00"),
        amount_max=Decimal("55.00"),
    ),
    TransactionTemplate(
        category_account_number="4200",
        counterparty="EDEKA",
        description="EDEKA Einkauf",
        amount_min=Decimal("22.00"),
        amount_max=Decimal("75.00"),
    ),
    TransactionTemplate(
        category_account_number="4200",
        counterparty="ALDI Nord",
        description="ALDI Einkauf",
        amount_min=Decimal("15.00"),
        amount_max=Decimal("45.00"),
    ),
    TransactionTemplate(
        category_account_number="4200",
        counterparty="Penny Markt",
        description="PENNY Einkauf",
        amount_min=Decimal("12.00"),
        amount_max=Decimal("35.00"),
    ),
]

# Restaurants & Bars (4210)
RESTAURANT_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4210",
        counterparty="Lieferando",
        description="LIEFERANDO Bestellung",
        amount_min=Decimal("18.00"),
        amount_max=Decimal("35.00"),
    ),
    TransactionTemplate(
        category_account_number="4210",
        counterparty="Vapiano SE",
        description="Vapiano Restaurant",
        amount_min=Decimal("14.00"),
        amount_max=Decimal("28.00"),
    ),
    TransactionTemplate(
        category_account_number="4210",
        counterparty="Starbucks",
        description="STARBUCKS COFFEE",
        amount_min=Decimal("4.50"),
        amount_max=Decimal("12.00"),
    ),
    TransactionTemplate(
        category_account_number="4210",
        counterparty="McDonald's",
        description="MCDONALDS",
        amount_min=Decimal("8.00"),
        amount_max=Decimal("18.00"),
    ),
]

# Transport (4300)
TRANSPORT_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4300",
        counterparty="BVG Berliner Verkehrsbetriebe",
        description="BVG Monatskarte",
        amount_min=Decimal("86.00"),
        amount_max=Decimal("86.00"),  # Fixed monthly ticket
    ),
    TransactionTemplate(
        category_account_number="4300",
        counterparty="DB Vertrieb GmbH",
        description="Deutsche Bahn Fahrkarte",
        amount_min=Decimal("19.90"),
        amount_max=Decimal("89.00"),
    ),
    TransactionTemplate(
        category_account_number="4300",
        counterparty="TIER Mobility",
        description="TIER E-Scooter",
        amount_min=Decimal("2.50"),
        amount_max=Decimal("8.00"),
    ),
    TransactionTemplate(
        category_account_number="4300",
        counterparty="Shell Deutschland",
        description="Shell Tankstelle",
        amount_min=Decimal("45.00"),
        amount_max=Decimal("75.00"),
    ),
]

# Clothing (4400)
CLOTHING_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4400",
        counterparty="Zalando SE",
        description="ZALANDO Bestellung",
        amount_min=Decimal("35.00"),
        amount_max=Decimal("120.00"),
    ),
    TransactionTemplate(
        category_account_number="4400",
        counterparty="H&M",
        description="H&M Einkauf",
        amount_min=Decimal("25.00"),
        amount_max=Decimal("85.00"),
    ),
]

# Fitness (4500)
FITNESS_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4500",
        counterparty="Urban Sports Club",
        description="Urban Sports Mitgliedschaft",
        amount_min=Decimal("49.00"),
        amount_max=Decimal("49.00"),  # Fixed monthly
    ),
]

# Health (4600)
HEALTH_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4600",
        counterparty="dm-drogerie markt",
        description="dm Einkauf",
        amount_min=Decimal("8.00"),
        amount_max=Decimal("35.00"),
    ),
    TransactionTemplate(
        category_account_number="4600",
        counterparty="Rossmann",
        description="Rossmann Einkauf",
        amount_min=Decimal("6.00"),
        amount_max=Decimal("28.00"),
    ),
    TransactionTemplate(
        category_account_number="4600",
        counterparty="Apotheke am Markt",
        description="Apotheke Einkauf",
        amount_min=Decimal("5.00"),
        amount_max=Decimal("45.00"),
    ),
]

# Subscriptions (4700) - Monthly
SUBSCRIPTION_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4700",
        counterparty="Netflix International",
        description="NETFLIX Abo",
        amount_min=Decimal("12.99"),
        amount_max=Decimal("12.99"),
    ),
    TransactionTemplate(
        category_account_number="4700",
        counterparty="Spotify AB",
        description="SPOTIFY Premium",
        amount_min=Decimal("9.99"),
        amount_max=Decimal("9.99"),
    ),
    TransactionTemplate(
        category_account_number="4700",
        counterparty="Amazon Europe",
        description="AMAZON PRIME",
        amount_min=Decimal("8.99"),
        amount_max=Decimal("8.99"),
    ),
    TransactionTemplate(
        category_account_number="4700",
        counterparty="Apple Distribution",
        description="iCloud+ Speicher",
        amount_min=Decimal("2.99"),
        amount_max=Decimal("2.99"),
    ),
]

# Entertainment (4800)
ENTERTAINMENT_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4800",
        counterparty="Steam Games",
        description="STEAM Purchase",
        amount_min=Decimal("9.99"),
        amount_max=Decimal("59.99"),
    ),
    TransactionTemplate(
        category_account_number="4800",
        counterparty="CinemaxX",
        description="CinemaxX Kino",
        amount_min=Decimal("12.00"),
        amount_max=Decimal("28.00"),
    ),
    TransactionTemplate(
        category_account_number="4800",
        counterparty="Eventim",
        description="Eventim Tickets",
        amount_min=Decimal("35.00"),
        amount_max=Decimal("95.00"),
    ),
]

# Miscellaneous (4900)
MISC_TEMPLATES: list[TransactionTemplate] = [
    TransactionTemplate(
        category_account_number="4900",
        counterparty="Amazon EU",
        description="AMAZON Bestellung",
        amount_min=Decimal("15.00"),
        amount_max=Decimal("120.00"),
    ),
    TransactionTemplate(
        category_account_number="4900",
        counterparty="PayPal Europe",
        description="PayPal Zahlung",
        amount_min=Decimal("10.00"),
        amount_max=Decimal("80.00"),
    ),
    TransactionTemplate(
        category_account_number="4900",
        counterparty="MediaMarkt",
        description="MediaMarkt Einkauf",
        amount_min=Decimal("25.00"),
        amount_max=Decimal("200.00"),
    ),
]


# =============================================================================
# Monthly Distribution (how many transactions per category per month)
# =============================================================================


@dataclass(frozen=True)
class MonthlyDistribution:
    """How many transactions to generate per month for each category."""

    templates: list[TransactionTemplate]
    min_per_month: int
    max_per_month: int
    is_fixed_monthly: bool = False  # True for rent, subscriptions, etc.


MONTHLY_DISTRIBUTIONS: list[MonthlyDistribution] = [
    # Fixed monthly expenses
    MonthlyDistribution(RENT_TEMPLATES, 1, 1, is_fixed_monthly=True),
    MonthlyDistribution(UTILITIES_TEMPLATES, 2, 3, is_fixed_monthly=True),
    MonthlyDistribution(SUBSCRIPTION_TEMPLATES, 4, 4, is_fixed_monthly=True),
    MonthlyDistribution(FITNESS_TEMPLATES, 1, 1, is_fixed_monthly=True),
    MonthlyDistribution([TRANSPORT_TEMPLATES[0]], 1, 1, is_fixed_monthly=True),  # BVG
    # Variable expenses
    MonthlyDistribution(GROCERY_TEMPLATES, 8, 12, is_fixed_monthly=False),
    MonthlyDistribution(RESTAURANT_TEMPLATES, 4, 7, is_fixed_monthly=False),
    MonthlyDistribution(
        TRANSPORT_TEMPLATES[1:], 2, 4, is_fixed_monthly=False
    ),  # DB, etc
    MonthlyDistribution(CLOTHING_TEMPLATES, 0, 2, is_fixed_monthly=False),
    MonthlyDistribution(HEALTH_TEMPLATES, 1, 3, is_fixed_monthly=False),
    MonthlyDistribution(ENTERTAINMENT_TEMPLATES, 1, 3, is_fixed_monthly=False),
    MonthlyDistribution(MISC_TEMPLATES, 2, 4, is_fixed_monthly=False),
]

# Income distribution
INCOME_DISTRIBUTION = MonthlyDistribution(
    templates=[INCOME_TEMPLATES[0]],  # Salary
    min_per_month=1,
    max_per_month=1,
    is_fixed_monthly=True,
)

# Occasional income (not every month)
OCCASIONAL_INCOME_DISTRIBUTION = MonthlyDistribution(
    templates=INCOME_TEMPLATES[1:],  # Refunds, tax returns
    min_per_month=0,
    max_per_month=1,
    is_fixed_monthly=False,
)


# =============================================================================
# Internal Transfers (between own accounts)
# =============================================================================


@dataclass(frozen=True)
class TransferTemplate:
    """Template for internal transfers between asset accounts."""

    from_account_number: str
    to_account_number: str
    description: str
    amount_min: Decimal
    amount_max: Decimal


TRANSFER_TEMPLATES: list[TransferTemplate] = [
    TransferTemplate(
        from_account_number="1010",  # DKB Girokonto
        to_account_number="1100",  # ING Tagesgeld
        description="Sparen",
        amount_min=Decimal("200.00"),
        amount_max=Decimal("400.00"),
    ),
]

TRANSFER_DISTRIBUTION = MonthlyDistribution(
    templates=[],  # Not used directly
    min_per_month=1,
    max_per_month=1,
    is_fixed_monthly=False,
)


# =============================================================================
# Demo User Configuration
# =============================================================================

# Using example.com (RFC 2606 reserved domain for documentation/examples)
DEMO_USER_EMAIL = "demo@example.com"
DEMO_USER_PASSWORD = "demo1234"
DEMO_USER_NAME = "Demo User"

DEMO_ADMIN_EMAIL = "admin@example.com"
DEMO_ADMIN_PASSWORD = "admin1234"
DEMO_ADMIN_NAME = "Demo Admin"

# Seed for reproducibility
RANDOM_SEED = 42

# Number of months of history to generate
MONTHS_OF_HISTORY = 6
