"""Integration tests for user preferences behavior edge cases.

These tests verify that user preferences correctly affect system behavior
without unintended side effects on existing data.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from swen.application.commands import (
    ResetUserPreferencesCommand,
    UpdateUserPreferencesCommand,
)
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.value_objects import Currency, Money
from swen.infrastructure.persistence.sqlalchemy.models import Base
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.user import (
    UserRepositorySQLAlchemy,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


from uuid import UUID

from swen.application.context import UserContext

TEST_EMAIL = "test@example.com"
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_CONTEXT = UserContext(user_id=TEST_USER_ID, email=TEST_EMAIL)


@pytest.fixture
async def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create a session from the engine."""
    session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_maker() as session:
        yield session


@pytest.fixture
def user_repo(session):
    """Create UserRepository instance."""
    return UserRepositorySQLAlchemy(session)


@pytest.fixture
def account_repo(session):
    """Create AccountRepository instance (user-scoped)."""
    return AccountRepositorySQLAlchemy(session, TEST_USER_CONTEXT)


@pytest.fixture
def transaction_repo(session, account_repo):
    """Create TransactionRepository instance (user-scoped)."""
    return TransactionRepositorySQLAlchemy(session, account_repo, TEST_USER_CONTEXT)


async def create_test_accounts(account_repo, session) -> tuple[Account, Account, Account]:
    """Create test accounts for transactions."""
    # Asset account (bank account)
    asset_account = Account(
        name="Test Bank Account",
        account_type=AccountType.ASSET,
        account_number="1000",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )

    # Expense account
    expense_account = Account(
        name="Groceries",
        account_type=AccountType.EXPENSE,
        account_number="4100",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )

    # Income account
    income_account = Account(
        name="Salary",
        account_type=AccountType.INCOME,
        account_number="3000",
        default_currency=Currency("EUR"),
        user_id=TEST_USER_ID,
    )

    await account_repo.save(asset_account)
    await account_repo.save(expense_account)
    await account_repo.save(income_account)
    await session.flush()

    return asset_account, expense_account, income_account


def create_expense_transaction(
    asset_account: Account,
    expense_account: Account,
    amount: Decimal,
    description: str,
    post: bool = False,
) -> Transaction:
    """Create an expense transaction (draft or posted)."""
    txn = Transaction(
        date=datetime.now(tz=timezone.utc),
        description=description,
        user_id=TEST_USER_ID,
    )
    money = Money(amount, Currency("EUR"))
    txn.add_debit(expense_account, money)  # Expense account debited
    txn.add_credit(asset_account, money)  # Asset account credited

    if post:
        txn.post()

    return txn


def create_income_transaction(
    asset_account: Account,
    income_account: Account,
    amount: Decimal,
    description: str,
    post: bool = False,
) -> Transaction:
    """Create an income transaction (draft or posted)."""
    txn = Transaction(
        date=datetime.now(tz=timezone.utc),
        description=description,
        user_id=TEST_USER_ID,
    )
    money = Money(amount, Currency("EUR"))
    txn.add_debit(asset_account, money)  # Asset account debited
    txn.add_credit(income_account, money)  # Income account credited

    if post:
        txn.post()

    return txn


class TestShowDraftTransactionsPreference:
    """
    Test Scenario 1: Dashboard visibility based on show_draft_transactions.

    User syncs data, sees dashboard with drafts visible (default),
    then changes preference to hide drafts and verifies behavior.
    """

    @pytest.mark.asyncio
    async def test_default_shows_all_transactions_including_drafts(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """Default preference shows both posted and draft transactions."""
        # Setup: Create accounts and transactions
        asset, expense, income = await create_test_accounts(account_repo, session)

        # Create mix of draft and posted transactions
        draft_txn = create_expense_transaction(
            asset, expense, Decimal("25.00"), "Draft expense", post=False
        )
        posted_txn = create_expense_transaction(
            asset, expense, Decimal("50.00"), "Posted expense", post=True
        )

        await transaction_repo.save(draft_txn)
        await transaction_repo.save(posted_txn)
        await session.flush()

        # Get user with default preferences
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)

        # Verify default is to show drafts
        assert user.preferences.display_settings.show_draft_transactions is True

        # Fetch all transactions (simulating dashboard behavior)
        all_transactions = await transaction_repo.find_all()

        # Should see both draft and posted
        assert len(all_transactions) == 2
        assert any(not t.is_posted for t in all_transactions)  # Has draft
        assert any(t.is_posted for t in all_transactions)  # Has posted

    @pytest.mark.asyncio
    async def test_changing_preference_hides_drafts(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """Changing show_draft_transactions to False filters out drafts."""
        # Setup: Create accounts and transactions
        asset, expense, income = await create_test_accounts(account_repo, session)

        # Create mix of draft and posted transactions
        draft_txn1 = create_expense_transaction(
            asset, expense, Decimal("25.00"), "Draft 1", post=False
        )
        draft_txn2 = create_expense_transaction(
            asset, expense, Decimal("30.00"), "Draft 2", post=False
        )
        posted_txn = create_expense_transaction(
            asset, expense, Decimal("50.00"), "Posted", post=True
        )

        await transaction_repo.save(draft_txn1)
        await transaction_repo.save(draft_txn2)
        await transaction_repo.save(posted_txn)
        await session.flush()

        # First: verify with default settings (show drafts)
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.display_settings.show_draft_transactions is True

        all_transactions = await transaction_repo.find_all()
        assert len(all_transactions) == 3

        # Now: change preference to hide drafts
        update_command = UpdateUserPreferencesCommand(user_repo)
        await update_command.execute(email=TEST_EMAIL, show_draft_transactions=False)
        await session.flush()

        # Verify preference changed
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.display_settings.show_draft_transactions is False

        # Fetch only posted transactions (simulating dashboard with new preference)
        posted_only = await transaction_repo.find_posted_transactions()

        # Should only see posted transaction
        assert len(posted_only) == 1
        assert posted_only[0].is_posted is True
        assert posted_only[0].description == "Posted"

    @pytest.mark.asyncio
    async def test_toggling_preference_back_shows_drafts_again(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """Toggling preference back to True shows drafts again."""
        # Setup: Create accounts and transactions
        asset, expense, income = await create_test_accounts(account_repo, session)

        draft_txn = create_expense_transaction(
            asset, expense, Decimal("25.00"), "Draft expense", post=False
        )
        posted_txn = create_expense_transaction(
            asset, expense, Decimal("50.00"), "Posted expense", post=True
        )

        await transaction_repo.save(draft_txn)
        await transaction_repo.save(posted_txn)
        await session.flush()

        update_command = UpdateUserPreferencesCommand(user_repo)

        # Hide drafts
        await update_command.execute(email=TEST_EMAIL, show_draft_transactions=False)
        await session.flush()

        posted_only = await transaction_repo.find_posted_transactions()
        assert len(posted_only) == 1

        # Show drafts again
        await update_command.execute(email=TEST_EMAIL, show_draft_transactions=True)
        await session.flush()

        all_transactions = await transaction_repo.find_all()
        assert len(all_transactions) == 2

        # Drafts are still drafts (not modified)
        drafts = [t for t in all_transactions if not t.is_posted]
        assert len(drafts) == 1
        assert drafts[0].description == "Draft expense"


class TestAutoPostTransactionsPreference:
    """
    Test Scenario 2: auto_post_transactions only affects NEW transactions.

    Changing the preference should NOT retroactively post existing drafts.
    Already posted transactions should remain untouched.
    """

    @pytest.mark.asyncio
    async def test_existing_drafts_not_affected_by_enabling_auto_post(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """Enabling auto_post_transactions does NOT post existing drafts."""
        # Setup: Create accounts and draft transactions with default settings
        asset, expense, income = await create_test_accounts(account_repo, session)

        # User starts with default (auto_post=False)
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.sync_settings.auto_post_transactions is False

        # Create draft transactions (simulating import with auto_post=False)
        draft1 = create_expense_transaction(
            asset, expense, Decimal("100.00"), "Existing draft 1", post=False
        )
        draft2 = create_expense_transaction(
            asset, expense, Decimal("200.00"), "Existing draft 2", post=False
        )

        await transaction_repo.save(draft1)
        await transaction_repo.save(draft2)
        await session.flush()

        # Verify drafts exist
        all_before = await transaction_repo.find_all()
        drafts_before = [t for t in all_before if not t.is_posted]
        assert len(drafts_before) == 2

        # NOW: Enable auto_post_transactions
        update_command = UpdateUserPreferencesCommand(user_repo)
        await update_command.execute(email=TEST_EMAIL, auto_post_transactions=True)
        await session.flush()

        # Verify preference changed
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.sync_settings.auto_post_transactions is True

        # CRITICAL: Existing drafts should STILL be drafts
        all_after = await transaction_repo.find_all()
        drafts_after = [t for t in all_after if not t.is_posted]

        assert len(drafts_after) == 2, "Existing drafts should NOT be auto-posted"
        for draft in drafts_after:
            assert draft.is_posted is False

    @pytest.mark.asyncio
    async def test_already_posted_transactions_remain_posted(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """Posted transactions remain posted regardless of preference changes."""
        # Setup
        asset, expense, income = await create_test_accounts(account_repo, session)
        await user_repo.get_or_create_by_email(TEST_EMAIL)

        # Create posted transactions
        posted1 = create_expense_transaction(
            asset, expense, Decimal("100.00"), "Posted expense 1", post=True
        )
        posted2 = create_income_transaction(
            asset, income, Decimal("500.00"), "Posted income", post=True
        )

        await transaction_repo.save(posted1)
        await transaction_repo.save(posted2)
        await session.flush()

        # Toggle auto_post multiple times
        update_command = UpdateUserPreferencesCommand(user_repo)

        await update_command.execute(email=TEST_EMAIL, auto_post_transactions=True)
        await session.flush()

        await update_command.execute(email=TEST_EMAIL, auto_post_transactions=False)
        await session.flush()

        await update_command.execute(email=TEST_EMAIL, auto_post_transactions=True)
        await session.flush()

        # Posted transactions should still be posted
        all_transactions = await transaction_repo.find_all()
        assert len(all_transactions) == 2
        assert all(t.is_posted for t in all_transactions)

    @pytest.mark.asyncio
    async def test_mixed_draft_and_posted_unaffected_by_preference_change(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """
        Mixed state of drafts and posted transactions is preserved
        when auto_post_transactions preference is changed.
        """
        # Setup
        asset, expense, income = await create_test_accounts(account_repo, session)
        await user_repo.get_or_create_by_email(TEST_EMAIL)

        # Create mix of draft and posted
        draft = create_expense_transaction(
            asset, expense, Decimal("50.00"), "Draft expense", post=False
        )
        posted = create_expense_transaction(
            asset, expense, Decimal("100.00"), "Posted expense", post=True
        )

        await transaction_repo.save(draft)
        await transaction_repo.save(posted)
        await session.flush()

        # Record original states
        all_before = await transaction_repo.find_all()
        draft_ids_before = {str(t.id) for t in all_before if not t.is_posted}
        posted_ids_before = {str(t.id) for t in all_before if t.is_posted}

        assert len(draft_ids_before) == 1
        assert len(posted_ids_before) == 1

        # Enable auto_post
        update_command = UpdateUserPreferencesCommand(user_repo)
        await update_command.execute(email=TEST_EMAIL, auto_post_transactions=True)
        await session.flush()

        # Verify states are preserved
        all_after = await transaction_repo.find_all()
        draft_ids_after = {str(t.id) for t in all_after if not t.is_posted}
        posted_ids_after = {str(t.id) for t in all_after if t.is_posted}

        assert draft_ids_after == draft_ids_before, "Drafts should remain drafts"
        assert posted_ids_after == posted_ids_before, "Posted should remain posted"


class TestResetPreferencesNoSideEffects:
    """
    Test Scenario 3: Resetting preferences doesn't affect transaction states.

    When user resets preferences to defaults, already-posted transactions
    should NOT be reverted to drafts.
    """

    @pytest.mark.asyncio
    async def test_reset_preferences_preserves_posted_transactions(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """Resetting preferences does NOT unpost transactions."""
        # Setup
        asset, expense, income = await create_test_accounts(account_repo, session)

        # User enables auto_post and creates posted transactions
        await user_repo.get_or_create_by_email(TEST_EMAIL)
        update_command = UpdateUserPreferencesCommand(user_repo)
        await update_command.execute(email=TEST_EMAIL, auto_post_transactions=True)
        await session.flush()

        # Create posted transactions
        posted1 = create_expense_transaction(
            asset, expense, Decimal("100.00"), "Posted 1", post=True
        )
        posted2 = create_expense_transaction(
            asset, expense, Decimal("200.00"), "Posted 2", post=True
        )

        await transaction_repo.save(posted1)
        await transaction_repo.save(posted2)
        await session.flush()

        # Verify all are posted
        all_before = await transaction_repo.find_all()
        assert all(t.is_posted for t in all_before)

        # RESET preferences to defaults
        reset_command = ResetUserPreferencesCommand(user_repo)
        await reset_command.execute(email=TEST_EMAIL)
        await session.flush()

        # Verify preferences are reset
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.sync_settings.auto_post_transactions is False

        # CRITICAL: Posted transactions should STILL be posted
        all_after = await transaction_repo.find_all()
        assert len(all_after) == 2
        assert all(t.is_posted for t in all_after), (
            "Resetting preferences should NOT unpost transactions"
        )

    @pytest.mark.asyncio
    async def test_reset_preferences_preserves_mixed_states(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """Resetting preferences preserves both draft and posted states."""
        # Setup
        asset, expense, income = await create_test_accounts(account_repo, session)
        await user_repo.get_or_create_by_email(TEST_EMAIL)

        # Create mix of states
        draft1 = create_expense_transaction(
            asset, expense, Decimal("25.00"), "Draft 1", post=False
        )
        draft2 = create_expense_transaction(
            asset, expense, Decimal("30.00"), "Draft 2", post=False
        )
        posted1 = create_expense_transaction(
            asset, expense, Decimal("100.00"), "Posted 1", post=True
        )
        posted2 = create_expense_transaction(
            asset, expense, Decimal("150.00"), "Posted 2", post=True
        )

        for txn in [draft1, draft2, posted1, posted2]:
            await transaction_repo.save(txn)
        await session.flush()

        # Change some preferences
        update_command = UpdateUserPreferencesCommand(user_repo)
        await update_command.execute(
            email=TEST_EMAIL,
            auto_post_transactions=True,
            show_draft_transactions=False,
            default_currency="USD",
        )
        await session.flush()

        # Record states before reset
        all_before = await transaction_repo.find_all()
        states_before = {str(t.id): t.is_posted for t in all_before}

        # Reset preferences
        reset_command = ResetUserPreferencesCommand(user_repo)
        await reset_command.execute(email=TEST_EMAIL)
        await session.flush()

        # Verify preferences are defaults
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.sync_settings.auto_post_transactions is False
        assert user.preferences.sync_settings.default_currency == "EUR"
        assert user.preferences.display_settings.show_draft_transactions is True

        # CRITICAL: Transaction states preserved
        all_after = await transaction_repo.find_all()
        states_after = {str(t.id): t.is_posted for t in all_after}

        assert states_after == states_before, (
            "Transaction states should be unchanged after reset"
        )


class TestPreferenceIsolation:
    """
    Additional edge case tests for preference isolation.
    """

    @pytest.mark.asyncio
    async def test_draft_transactions_can_still_be_manually_posted(
        self, session, user_repo, account_repo, transaction_repo
    ):
        """
        Even with auto_post=False, drafts can be manually posted.
        Preference only affects automatic behavior.
        """
        # Setup
        asset, expense, income = await create_test_accounts(account_repo, session)
        user = await user_repo.get_or_create_by_email(TEST_EMAIL)

        # Ensure auto_post is False
        assert user.preferences.sync_settings.auto_post_transactions is False

        # Create draft
        draft = create_expense_transaction(
            asset, expense, Decimal("100.00"), "Manual post test", post=False
        )
        await transaction_repo.save(draft)
        await session.flush()

        # Verify it's a draft
        txn = await transaction_repo.find_by_id(draft.id)
        assert txn.is_posted is False

        # Manually post it
        txn.post()
        await transaction_repo.save(txn)
        await session.flush()

        # Verify it's now posted
        txn = await transaction_repo.find_by_id(draft.id)
        assert txn.is_posted is True

    @pytest.mark.asyncio
    async def test_preferences_persist_across_sessions(
        self, engine
    ):
        """Preferences persist correctly across database sessions."""
        session_maker = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Session 1: Change preferences
        async with session_maker() as session1:
            repo1 = UserRepositorySQLAlchemy(session1)
            user = await repo1.get_or_create_by_email(TEST_EMAIL)
            user.update_preferences(
                auto_post_transactions=True,
                default_currency="CHF",
                show_draft_transactions=False,
                default_date_range_days=60,
            )
            await repo1.save(user)
            await session1.commit()

        # Session 2: Verify preferences persisted
        async with session_maker() as session2:
            repo2 = UserRepositorySQLAlchemy(session2)
            user = await repo2.get_or_create_by_email(TEST_EMAIL)

            assert user.preferences.sync_settings.auto_post_transactions is True
            assert user.preferences.sync_settings.default_currency == "CHF"
            assert user.preferences.display_settings.show_draft_transactions is False
            assert user.preferences.display_settings.default_date_range_days == 60

    @pytest.mark.asyncio
    async def test_multiple_preference_updates_are_cumulative(
        self, session, user_repo
    ):
        """Multiple partial updates accumulate correctly."""
        await user_repo.get_or_create_by_email(TEST_EMAIL)
        update_command = UpdateUserPreferencesCommand(user_repo)

        # First update: just auto_post
        await update_command.execute(email=TEST_EMAIL, auto_post_transactions=True)
        await session.flush()

        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.sync_settings.auto_post_transactions is True
        assert user.preferences.display_settings.show_draft_transactions is True  # Default

        # Second update: just show_drafts
        await update_command.execute(email=TEST_EMAIL, show_draft_transactions=False)
        await session.flush()

        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        # Both should reflect their updates
        assert user.preferences.sync_settings.auto_post_transactions is True
        assert user.preferences.display_settings.show_draft_transactions is False

        # Third update: just currency
        await update_command.execute(email=TEST_EMAIL, default_currency="GBP")
        await session.flush()

        user = await user_repo.get_or_create_by_email(TEST_EMAIL)
        assert user.preferences.sync_settings.auto_post_transactions is True
        assert user.preferences.sync_settings.default_currency == "GBP"
        assert user.preferences.display_settings.show_draft_transactions is False
