"""Demo data seeding for SWEN.

This script generates a fully functional demo account with realistic
German personal finance transactions for screenshots and demonstrations.

The demo user is always recreated with fresh data for reproducibility.

Usage:
    poetry run seed-demo
    # or
    python -m swen_demo.seed
    # or
    make seed-demo

Options:
    --dry-run   Show what would be created without writing to database
"""

import asyncio
import logging
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from swen.application.commands.accounting import (
    CreateTransactionCommand,
    GenerateDefaultAccountsCommand,
    PostTransactionCommand,
)
from swen.application.ports.identity.current_user import CurrentUser
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import (
    Currency,
    JournalEntryInput,
    TransactionSource,
)
from swen.domain.shared.time import utc_now
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    SQLAlchemyRepositoryFactory,
)
from swen.presentation.api.dependencies import (
    create_tables,
    get_encryption_key,
    get_session_maker,
)
from swen_config.settings import get_settings
from swen_demo.data import (
    DEMO_ASSET_ACCOUNTS,
    DEMO_USER_EMAIL,
    DEMO_USER_PASSWORD,
    INCOME_DISTRIBUTION,
    MONTHLY_DISTRIBUTIONS,
    MONTHS_OF_HISTORY,
    OCCASIONAL_INCOME_DISTRIBUTION,
    RANDOM_SEED,
    TRANSFER_DISTRIBUTION,
    TRANSFER_TEMPLATES,
    AssetAccountDef,
    MonthlyDistribution,
)
from swen_identity import PasswordHashingService
from swen_identity.domain.user import User, UserRole
from swen_identity.infrastructure.persistence.sqlalchemy import (
    UserCredentialRepositorySQLAlchemy,
    UserRepositorySQLAlchemy,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass
class SeedStats:
    """Statistics about what was seeded."""

    user_created: bool
    user_id: UUID
    asset_accounts_created: int
    category_accounts_created: int
    transactions_created: int
    transactions_posted: int


async def create_demo_user(session: AsyncSession) -> User:
    """Create demo user, deleting any existing one first.

    Parameters
    ----------
    session
        Database session

    Returns
    -------
    Freshly created demo user
    """
    user_repo = UserRepositorySQLAlchemy(session)
    credential_repo = UserCredentialRepositorySQLAlchemy(session)
    password_service = PasswordHashingService()

    existing = await user_repo.find_by_email(DEMO_USER_EMAIL)

    if existing:
        logger.info("Deleting existing demo user: %s", existing.id)
        await user_repo.delete_with_all_data(existing.id)

    # Create new demo user
    logger.info("Creating demo user: %s", DEMO_USER_EMAIL)
    user = User.create(DEMO_USER_EMAIL, role=UserRole.USER)
    password_hash = password_service.hash(DEMO_USER_PASSWORD)

    await user_repo.save(user)
    await credential_repo.save(user_id=user.id, password_hash=password_hash)

    return user


def create_current_user(user: User) -> CurrentUser:
    """Create a CurrentUser from a User entity."""
    return CurrentUser(
        user_id=user.id,
        email=user.email,
        is_admin=user.is_admin,
    )


async def create_asset_accounts(
    factory: SQLAlchemyRepositoryFactory,
    account_defs: list[AssetAccountDef],
) -> dict[str, Account]:
    """Create asset accounts and return a mapping of account_number -> Account."""
    account_repo = factory.account_repository()
    user_id = factory.current_user.user_id
    accounts: dict[str, Account] = {}

    for acc_def in account_defs:
        # Check if account already exists
        existing = await account_repo.find_by_account_number(acc_def.account_number)
        if existing:
            logger.debug("Asset account already exists: %s", acc_def.name)
            accounts[acc_def.account_number] = existing
            continue

        account = Account(
            name=acc_def.name,
            account_type=AccountType.ASSET,
            account_number=acc_def.account_number,
            user_id=user_id,
            iban=acc_def.iban,
            default_currency=Currency("EUR"),
            description=acc_def.description,
        )
        await account_repo.save(account)
        accounts[acc_def.account_number] = account
        logger.info(
            "Created asset account: %s (%s)",
            acc_def.name,
            acc_def.iban or "no IBAN",
        )

    return accounts


async def create_default_category_accounts(
    factory: SQLAlchemyRepositoryFactory,
) -> int:
    """Create default income/expense accounts using the minimal template."""
    command = GenerateDefaultAccountsCommand.from_factory(factory)
    result = await command.execute()

    if result.get("skipped"):
        logger.info("Category accounts already exist, skipping")
        return 0

    total = result.get("total", 0)
    logger.info("Created %d category accounts", total)
    return total


async def create_opening_balances(
    factory: SQLAlchemyRepositoryFactory,
    asset_accounts: dict[str, Account],
    asset_defs: list[AssetAccountDef],
    balance_date: datetime,
) -> int:
    """Create opening balance transactions for asset accounts."""
    account_repo = factory.account_repository()
    create_cmd = CreateTransactionCommand.from_factory(factory)
    post_cmd = PostTransactionCommand.from_factory(factory)

    # Get the opening balance (equity) account
    equity_account = await account_repo.find_by_account_number("2000")
    if not equity_account:
        logger.warning(
            "Opening balance account (2000) not found, skipping opening balances",
        )
        return 0

    created = 0
    for acc_def in asset_defs:
        if acc_def.opening_balance == Decimal("0"):
            continue

        asset_account = asset_accounts.get(acc_def.account_number)
        if not asset_account:
            continue

        # Create opening balance transaction
        # Debit Asset (increase), Credit Equity (increase)
        entries = [
            JournalEntryInput.debit_entry(asset_account.id, acc_def.opening_balance),
            JournalEntryInput.credit_entry(equity_account.id, acc_def.opening_balance),
        ]

        txn = await create_cmd.execute(
            description=f"Anfangssaldo - {acc_def.name}",
            entries=entries,
            date=balance_date,
            source=TransactionSource.OPENING_BALANCE,
        )
        await post_cmd.execute(txn.id)
        created += 1
        logger.debug(
            "Created opening balance for %s: €%.2f",
            acc_def.name,
            acc_def.opening_balance,
        )

    logger.info("Created %d opening balance transactions", created)
    return created


def generate_transaction_dates(
    start_date: datetime,
    end_date: datetime,
    distribution: MonthlyDistribution,
    rng: random.Random,
) -> list[datetime]:
    """Generate transaction dates based on monthly distribution."""
    dates = []
    current = start_date.replace(day=1)

    while current < end_date:
        # Determine month end
        if current.month == 12:
            next_month = current.replace(year=current.year + 1, month=1)
        else:
            next_month = current.replace(month=current.month + 1)
        month_end = next_month - timedelta(days=1)

        # Limit to end_date
        month_end = min(month_end, end_date)

        # Determine number of transactions this month
        if distribution.is_fixed_monthly:
            count = distribution.min_per_month
        else:
            count = rng.randint(distribution.min_per_month, distribution.max_per_month)

        # Generate random dates within the month
        for _ in range(count):
            if distribution.is_fixed_monthly:
                # Fixed expenses typically on specific days (1st, 15th, etc.)
                day = rng.choice([1, 5, 10, 15, 25])
                day = min(day, month_end.day)
            else:
                day = rng.randint(1, month_end.day)

            txn_date = current.replace(day=day)
            if txn_date <= end_date:
                dates.append(txn_date)

        current = next_month

    return dates


async def generate_transactions(
    factory: SQLAlchemyRepositoryFactory,
    asset_accounts: dict[str, Account],
    rng: random.Random,
    start_date: datetime,
    end_date: datetime,
) -> tuple[int, int]:
    """Generate realistic transactions based on templates.

    Returns tuple of (created_count, posted_count).
    """
    account_repo = factory.account_repository()
    create_cmd = CreateTransactionCommand.from_factory(factory)
    post_cmd = PostTransactionCommand.from_factory(factory)

    # Cache category accounts
    category_accounts: dict[str, Account] = {}

    async def get_category_account(account_number: str) -> Optional[Account]:
        if account_number not in category_accounts:
            account = await account_repo.find_by_account_number(account_number)
            if account:
                category_accounts[account_number] = account
        return category_accounts.get(account_number)

    # Primary payment account (DKB Girokonto)
    primary_asset = asset_accounts.get("1000")
    if not primary_asset:
        logger.error("Primary asset account (1000) not found")
        return 0, 0

    created = 0
    posted = 0

    # Generate income transactions
    logger.info("Generating income transactions...")
    income_dates = generate_transaction_dates(
        start_date,
        end_date,
        INCOME_DISTRIBUTION,
        rng,
    )
    for txn_date in income_dates:
        template = rng.choice(INCOME_DISTRIBUTION.templates)
        category = await get_category_account(template.category_account_number)
        if not category:
            continue

        amount = template.amount_min + (
            template.amount_max - template.amount_min
        ) * Decimal(str(rng.random()))
        amount = amount.quantize(Decimal("0.01"))

        # Update description with month
        month_name = txn_date.strftime("%B %Y")
        description = f"Gehalt {month_name}"

        # Income: Debit Asset, Credit Income
        entries = [
            JournalEntryInput.debit_entry(primary_asset.id, amount),
            JournalEntryInput.credit_entry(category.id, amount),
        ]

        txn = await create_cmd.execute(
            description=description,
            entries=entries,
            counterparty=template.counterparty,
            counterparty_iban=template.counterparty_iban,
            date=txn_date,
            source=TransactionSource.MANUAL,
            source_iban=primary_asset.iban,
        )
        await post_cmd.execute(txn.id)
        created += 1
        posted += 1

    # Generate occasional income (refunds, etc.)
    occasional_dates = generate_transaction_dates(
        start_date,
        end_date,
        OCCASIONAL_INCOME_DISTRIBUTION,
        rng,
    )
    for txn_date in occasional_dates:
        if not OCCASIONAL_INCOME_DISTRIBUTION.templates:
            continue
        template = rng.choice(OCCASIONAL_INCOME_DISTRIBUTION.templates)
        category = await get_category_account(template.category_account_number)
        if not category:
            continue

        amount = template.amount_min + (
            template.amount_max - template.amount_min
        ) * Decimal(str(rng.random()))
        amount = amount.quantize(Decimal("0.01"))

        entries = [
            JournalEntryInput.debit_entry(primary_asset.id, amount),
            JournalEntryInput.credit_entry(category.id, amount),
        ]

        txn = await create_cmd.execute(
            description=template.description,
            entries=entries,
            counterparty=template.counterparty,
            date=txn_date,
            source=TransactionSource.MANUAL,
            source_iban=primary_asset.iban,
        )
        await post_cmd.execute(txn.id)
        created += 1
        posted += 1

    # Generate expense transactions
    logger.info("Generating expense transactions...")
    for distribution in MONTHLY_DISTRIBUTIONS:
        dates = generate_transaction_dates(start_date, end_date, distribution, rng)

        for txn_date in dates:
            if not distribution.templates:
                continue
            template = rng.choice(distribution.templates)
            category = await get_category_account(template.category_account_number)
            if not category:
                continue

            amount = template.amount_min + (
                template.amount_max - template.amount_min
            ) * Decimal(str(rng.random()))
            amount = amount.quantize(Decimal("0.01"))

            # Expense: Debit Expense, Credit Asset
            entries = [
                JournalEntryInput.debit_entry(category.id, amount),
                JournalEntryInput.credit_entry(primary_asset.id, amount),
            ]

            txn = await create_cmd.execute(
                description=template.description,
                entries=entries,
                counterparty=template.counterparty,
                counterparty_iban=template.counterparty_iban,
                date=txn_date,
                source=TransactionSource.MANUAL,
                source_iban=primary_asset.iban,
            )
            await post_cmd.execute(txn.id)
            created += 1
            posted += 1

    # Generate internal transfers
    logger.info("Generating internal transfers...")
    transfer_dates = generate_transaction_dates(
        start_date,
        end_date,
        TRANSFER_DISTRIBUTION,
        rng,
    )
    for txn_date in transfer_dates:
        if not TRANSFER_TEMPLATES:
            continue
        template = rng.choice(TRANSFER_TEMPLATES)
        from_account = asset_accounts.get(template.from_account_number)
        to_account = asset_accounts.get(template.to_account_number)
        if not from_account or not to_account:
            continue

        amount = template.amount_min + (
            template.amount_max - template.amount_min
        ) * Decimal(str(rng.random()))
        amount = amount.quantize(Decimal("0.01"))

        # Transfer: Debit destination, Credit source
        entries = [
            JournalEntryInput.debit_entry(to_account.id, amount),
            JournalEntryInput.credit_entry(from_account.id, amount),
        ]

        txn = await create_cmd.execute(
            description=template.description,
            entries=entries,
            date=txn_date,
            source=TransactionSource.MANUAL,
            is_internal_transfer=True,
        )
        await post_cmd.execute(txn.id)
        created += 1
        posted += 1

    logger.info("Generated %d transactions (%d posted)", created, posted)
    return created, posted


async def seed_demo_data(dry_run: bool = False) -> SeedStats:
    """Main seeding function.

    Always recreates demo user with fresh data for reproducible screenshots.

    Parameters
    ----------
    dry_run
        Show what would be created without writing

    Returns
    -------
    Statistics about what was seeded
    """
    if dry_run:
        logger.info("DRY RUN - no data will be written")
        # For dry run, just show what would happen
        return SeedStats(
            user_created=True,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            asset_accounts_created=len(DEMO_ASSET_ACCOUNTS),
            category_accounts_created=14,
            transactions_created=100,
            transactions_posted=100,
        )

    # Initialize random with fixed seed for reproducibility
    rng = random.Random(RANDOM_SEED)

    # Ensure tables exist
    await create_tables()

    session_maker = get_session_maker()

    async with session_maker() as session:
        # Create demo user (deletes existing if present)
        user = await create_demo_user(session)

        # Create current user context
        current_user = create_current_user(user)

        # Create repository factory
        factory = SQLAlchemyRepositoryFactory(
            session=session,
            current_user=current_user,
            encryption_key=get_encryption_key(),
        )

        # Create asset accounts
        asset_accounts = await create_asset_accounts(factory, DEMO_ASSET_ACCOUNTS)
        asset_count = len([a for a in asset_accounts.values()])

        # Create category accounts (income/expense)
        category_count = await create_default_category_accounts(factory)

        # Calculate date range
        end_date = utc_now() - timedelta(days=1)  # Yesterday
        start_date = end_date - timedelta(days=MONTHS_OF_HISTORY * 30)

        # Create opening balances
        await create_opening_balances(
            factory,
            asset_accounts,
            DEMO_ASSET_ACCOUNTS,
            start_date - timedelta(days=1),  # Day before first transaction
        )

        # Generate transactions
        txn_created, txn_posted = await generate_transactions(
            factory,
            asset_accounts,
            rng,
            start_date,
            end_date,
        )

        # Commit all changes
        await session.commit()

        logger.info("=" * 50)
        logger.info("Demo data seeding complete!")
        logger.info("=" * 50)
        logger.info("  User: %s", DEMO_USER_EMAIL)
        logger.info("  Password: %s", DEMO_USER_PASSWORD)
        logger.info("  Asset accounts: %d", asset_count)
        logger.info("  Category accounts: %d", category_count)
        logger.info("  Transactions: %d", txn_created)
        logger.info("=" * 50)

        return SeedStats(
            user_created=True,
            user_id=user.id,
            asset_accounts_created=asset_count,
            category_accounts_created=category_count,
            transactions_created=txn_created,
            transactions_posted=txn_posted,
        )


def main():
    """CLI entry point."""
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        sys.exit(0)

    logger.info("SWEN Demo Data Seeder")
    logger.info("=" * 50)

    settings = get_settings()
    db_url = settings.database_url
    db_display = db_url.split("@")[-1] if "@" in db_url else db_url
    logger.info("Database: %s", db_display)

    asyncio.run(seed_demo_data(dry_run=dry_run))


if __name__ == "__main__":
    main()
