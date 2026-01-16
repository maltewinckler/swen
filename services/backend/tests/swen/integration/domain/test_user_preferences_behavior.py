"""Integration tests for user settings behavior edge cases.

These tests verify that user settings correctly affect system behavior
without unintended side effects on existing data.

Uses Testcontainers PostgreSQL for isolated, ephemeral database instances.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from swen.application.ports.identity import CurrentUser
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.value_objects import Currency, Money
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.settings import (
    UserSettingsRepositorySQLAlchemy,
)
from swen_identity.infrastructure.persistence.sqlalchemy import (
    UserRepositorySQLAlchemy,
)

# Import Testcontainers fixtures
from tests.shared.fixtures.database import (
    TEST_USER_EMAIL,
    TEST_USER_ID,
)

TEST_USER_CONTEXT = CurrentUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


@pytest.fixture
def user_repo(db_session):
    """Create UserRepository instance."""
    return UserRepositorySQLAlchemy(db_session)


@pytest.fixture
def settings_repo(db_session):
    """Create UserSettingsRepository instance (user-scoped)."""
    return UserSettingsRepositorySQLAlchemy(db_session, TEST_USER_CONTEXT)


@pytest.fixture
def account_repo(db_session):
    """Create AccountRepository instance (user-scoped)."""
    return AccountRepositorySQLAlchemy(db_session, TEST_USER_CONTEXT)


@pytest.fixture
def transaction_repo(db_session, account_repo):
    """Create TransactionRepository instance (user-scoped)."""
    return TransactionRepositorySQLAlchemy(db_session, account_repo, TEST_USER_CONTEXT)


async def setup_test_user(user_repo, db_session) -> None:
    """Create the test user for FK constraints.

    Note: The shared db_session fixture already creates test users,
    but we may need to handle this differently if test expects specific user.
    """
    # The shared fixture already creates TEST_USER_ID, so this is a no-op
    # if the user already exists. Just flush to ensure consistency.
    await db_session.flush()


async def create_test_accounts(
    account_repo, db_session
) -> tuple[Account, Account, Account]:
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
    await db_session.flush()

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
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """Default preference shows both posted and draft transactions."""
        # Setup: Create user and accounts
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        # Create mix of draft and posted transactions
        draft_txn = create_expense_transaction(
            asset,
            expense,
            Decimal("25.00"),
            "Draft expense",
            post=False,
        )
        posted_txn = create_expense_transaction(
            asset,
            expense,
            Decimal("50.00"),
            "Posted expense",
            post=True,
        )

        await transaction_repo.save(draft_txn)
        await transaction_repo.save(posted_txn)
        await db_session.flush()

        # Get settings with defaults
        settings = await settings_repo.get_or_create()

        # Verify default is to show drafts
        assert settings.display.show_draft_transactions is True

        # Fetch all transactions (simulating dashboard behavior)
        all_transactions = await transaction_repo.find_all()

        # Should see both draft and posted
        assert len(all_transactions) == 2
        assert any(not t.is_posted for t in all_transactions)  # Has draft
        assert any(t.is_posted for t in all_transactions)  # Has posted

    @pytest.mark.asyncio
    async def test_changing_preference_hides_drafts(
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """Changing show_draft_transactions to False filters out drafts."""
        # Setup: Create user and accounts
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        # Create mix of draft and posted transactions
        draft_txn1 = create_expense_transaction(
            asset,
            expense,
            Decimal("25.00"),
            "Draft 1",
            post=False,
        )
        draft_txn2 = create_expense_transaction(
            asset,
            expense,
            Decimal("30.00"),
            "Draft 2",
            post=False,
        )
        posted_txn = create_expense_transaction(
            asset,
            expense,
            Decimal("50.00"),
            "Posted",
            post=True,
        )

        await transaction_repo.save(draft_txn1)
        await transaction_repo.save(draft_txn2)
        await transaction_repo.save(posted_txn)
        await db_session.flush()

        # First: verify with default settings (show drafts)
        settings = await settings_repo.get_or_create()
        assert settings.display.show_draft_transactions is True

        all_transactions = await transaction_repo.find_all()
        assert len(all_transactions) == 3

        # Now: change setting to hide drafts
        settings.update_display(show_draft_transactions=False)
        await settings_repo.save(settings)
        await db_session.flush()

        # Verify setting changed
        settings = await settings_repo.find()
        assert settings.display.show_draft_transactions is False

        # Fetch only posted transactions (simulating dashboard with new preference)
        posted_only = await transaction_repo.find_posted_transactions()

        # Should only see posted transaction
        assert len(posted_only) == 1
        assert posted_only[0].is_posted is True
        assert posted_only[0].description == "Posted"

    @pytest.mark.asyncio
    async def test_toggling_preference_back_shows_drafts_again(
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """Toggling preference back to True shows drafts again."""
        # Setup: Create user and accounts
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        draft_txn = create_expense_transaction(
            asset,
            expense,
            Decimal("25.00"),
            "Draft expense",
            post=False,
        )
        posted_txn = create_expense_transaction(
            asset,
            expense,
            Decimal("50.00"),
            "Posted expense",
            post=True,
        )

        await transaction_repo.save(draft_txn)
        await transaction_repo.save(posted_txn)
        await db_session.flush()

        settings = await settings_repo.get_or_create()

        # Hide drafts
        settings.update_display(show_draft_transactions=False)
        await settings_repo.save(settings)
        await db_session.flush()

        posted_only = await transaction_repo.find_posted_transactions()
        assert len(posted_only) == 1

        # Show drafts again
        settings = await settings_repo.find()
        settings.update_display(show_draft_transactions=True)
        await settings_repo.save(settings)
        await db_session.flush()

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
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """Enabling auto_post_transactions does NOT post existing drafts."""
        # Setup: Create user and accounts with default settings
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        # Settings start with default (auto_post=False)
        settings = await settings_repo.get_or_create()
        assert settings.sync.auto_post_transactions is False

        # Create draft transactions (simulating import with auto_post=False)
        draft1 = create_expense_transaction(
            asset,
            expense,
            Decimal("100.00"),
            "Existing draft 1",
            post=False,
        )
        draft2 = create_expense_transaction(
            asset,
            expense,
            Decimal("200.00"),
            "Existing draft 2",
            post=False,
        )

        await transaction_repo.save(draft1)
        await transaction_repo.save(draft2)
        await db_session.flush()

        # Verify drafts exist
        all_before = await transaction_repo.find_all()
        drafts_before = [t for t in all_before if not t.is_posted]
        assert len(drafts_before) == 2

        # NOW: Enable auto_post_transactions
        settings.update_sync(auto_post_transactions=True)
        await settings_repo.save(settings)
        await db_session.flush()

        # Verify setting changed
        settings = await settings_repo.find()
        assert settings.sync.auto_post_transactions is True

        # CRITICAL: Existing drafts should STILL be drafts
        all_after = await transaction_repo.find_all()
        drafts_after = [t for t in all_after if not t.is_posted]

        assert len(drafts_after) == 2, "Existing drafts should NOT be auto-posted"
        for draft in drafts_after:
            assert draft.is_posted is False

    @pytest.mark.asyncio
    async def test_already_posted_transactions_remain_posted(
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """Posted transactions remain posted regardless of preference changes."""
        # Setup
        await setup_test_user(user_repo, db_session)
        asset, expense, income = await create_test_accounts(account_repo, db_session)

        # Create posted transactions
        posted1 = create_expense_transaction(
            asset,
            expense,
            Decimal("100.00"),
            "Posted expense 1",
            post=True,
        )
        posted2 = create_income_transaction(
            asset,
            income,
            Decimal("500.00"),
            "Posted income",
            post=True,
        )

        await transaction_repo.save(posted1)
        await transaction_repo.save(posted2)
        await db_session.flush()

        # Toggle auto_post multiple times
        settings = await settings_repo.get_or_create()

        settings.update_sync(auto_post_transactions=True)
        await settings_repo.save(settings)
        await db_session.flush()

        settings = await settings_repo.find()
        settings.update_sync(auto_post_transactions=False)
        await settings_repo.save(settings)
        await db_session.flush()

        settings = await settings_repo.find()
        settings.update_sync(auto_post_transactions=True)
        await settings_repo.save(settings)
        await db_session.flush()

        # Posted transactions should still be posted
        all_transactions = await transaction_repo.find_all()
        assert len(all_transactions) == 2
        assert all(t.is_posted for t in all_transactions)

    @pytest.mark.asyncio
    async def test_mixed_draft_and_posted_unaffected_by_preference_change(
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """
        Mixed state of drafts and posted transactions is preserved
        when auto_post_transactions preference is changed.
        """
        # Setup
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        # Create mix of draft and posted
        draft = create_expense_transaction(
            asset,
            expense,
            Decimal("50.00"),
            "Draft expense",
            post=False,
        )
        posted = create_expense_transaction(
            asset,
            expense,
            Decimal("100.00"),
            "Posted expense",
            post=True,
        )

        await transaction_repo.save(draft)
        await transaction_repo.save(posted)
        await db_session.flush()

        # Record original states
        all_before = await transaction_repo.find_all()
        draft_ids_before = {str(t.id) for t in all_before if not t.is_posted}
        posted_ids_before = {str(t.id) for t in all_before if t.is_posted}

        assert len(draft_ids_before) == 1
        assert len(posted_ids_before) == 1

        # Enable auto_post
        settings = await settings_repo.get_or_create()
        settings.update_sync(auto_post_transactions=True)
        await settings_repo.save(settings)
        await db_session.flush()

        # Verify states are preserved
        all_after = await transaction_repo.find_all()
        draft_ids_after = {str(t.id) for t in all_after if not t.is_posted}
        posted_ids_after = {str(t.id) for t in all_after if t.is_posted}

        assert draft_ids_after == draft_ids_before, "Drafts should remain drafts"
        assert posted_ids_after == posted_ids_before, "Posted should remain posted"


class TestResetPreferencesNoSideEffects:
    """
    Test Scenario 3: Resetting settings doesn't affect transaction states.

    When user resets settings to defaults, already-posted transactions
    should NOT be reverted to drafts.
    """

    @pytest.mark.asyncio
    async def test_reset_preferences_preserves_posted_transactions(
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """Resetting settings does NOT unpost transactions."""
        # Setup
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        # User enables auto_post and creates posted transactions
        settings = await settings_repo.get_or_create()
        settings.update_sync(auto_post_transactions=True)
        await settings_repo.save(settings)
        await db_session.flush()

        # Create posted transactions
        posted1 = create_expense_transaction(
            asset,
            expense,
            Decimal("100.00"),
            "Posted 1",
            post=True,
        )
        posted2 = create_expense_transaction(
            asset,
            expense,
            Decimal("200.00"),
            "Posted 2",
            post=True,
        )

        await transaction_repo.save(posted1)
        await transaction_repo.save(posted2)
        await db_session.flush()

        # Verify all are posted
        all_before = await transaction_repo.find_all()
        assert all(t.is_posted for t in all_before)

        # RESET settings to defaults
        settings = await settings_repo.find()
        settings.reset()
        await settings_repo.save(settings)
        await db_session.flush()

        # Verify settings are reset
        settings = await settings_repo.find()
        assert settings.sync.auto_post_transactions is False

        # CRITICAL: Posted transactions should STILL be posted
        all_after = await transaction_repo.find_all()
        assert len(all_after) == 2
        assert all(t.is_posted for t in all_after), (
            "Resetting settings should NOT unpost transactions"
        )

    @pytest.mark.asyncio
    async def test_reset_preferences_preserves_mixed_states(
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """Resetting settings preserves both draft and posted states."""
        # Setup
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        # Create mix of states
        draft1 = create_expense_transaction(
            asset,
            expense,
            Decimal("25.00"),
            "Draft 1",
            post=False,
        )
        draft2 = create_expense_transaction(
            asset,
            expense,
            Decimal("30.00"),
            "Draft 2",
            post=False,
        )
        posted1 = create_expense_transaction(
            asset,
            expense,
            Decimal("100.00"),
            "Posted 1",
            post=True,
        )
        posted2 = create_expense_transaction(
            asset,
            expense,
            Decimal("150.00"),
            "Posted 2",
            post=True,
        )

        for txn in [draft1, draft2, posted1, posted2]:
            await transaction_repo.save(txn)
        await db_session.flush()

        # Change some settings
        settings = await settings_repo.get_or_create()
        settings.update_sync(auto_post_transactions=True, default_currency="USD")
        settings.update_display(show_draft_transactions=False)
        await settings_repo.save(settings)
        await db_session.flush()

        # Record states before reset
        all_before = await transaction_repo.find_all()
        states_before = {str(t.id): t.is_posted for t in all_before}

        # Reset settings
        settings = await settings_repo.find()
        settings.reset()
        await settings_repo.save(settings)
        await db_session.flush()

        # Verify settings are defaults
        settings = await settings_repo.find()
        assert settings.sync.auto_post_transactions is False
        assert settings.sync.default_currency == "EUR"
        assert settings.display.show_draft_transactions is True

        # CRITICAL: Transaction states preserved
        all_after = await transaction_repo.find_all()
        states_after = {str(t.id): t.is_posted for t in all_after}

        assert states_after == states_before, (
            "Transaction states should be unchanged after reset"
        )


class TestPreferenceIsolation:
    """
    Additional edge case tests for settings isolation.
    """

    @pytest.mark.asyncio
    async def test_draft_transactions_can_still_be_manually_posted(
        self,
        db_session,
        user_repo,
        settings_repo,
        account_repo,
        transaction_repo,
    ):
        """
        Even with auto_post=False, drafts can be manually posted.
        Preference only affects automatic behavior.
        """
        # Setup
        await setup_test_user(user_repo, db_session)
        asset, expense, _income = await create_test_accounts(account_repo, db_session)

        # Ensure auto_post is False
        settings = await settings_repo.get_or_create()
        assert settings.sync.auto_post_transactions is False

        # Create draft
        draft = create_expense_transaction(
            asset,
            expense,
            Decimal("100.00"),
            "Manual post test",
            post=False,
        )
        await transaction_repo.save(draft)
        await db_session.flush()

        # Verify it's a draft
        txn = await transaction_repo.find_by_id(draft.id)
        assert txn.is_posted is False

        # Manually post it
        txn.post()
        await transaction_repo.save(txn)
        await db_session.flush()

        # Verify it's now posted
        txn = await transaction_repo.find_by_id(draft.id)
        assert txn.is_posted is True

    @pytest.mark.asyncio
    async def test_preferences_persist_across_sessions(
        self,
        async_engine,
        user_repo,
        db_session,
    ):
        """Settings persist correctly across database sessions."""
        await setup_test_user(user_repo, db_session)
        await db_session.commit()

        session_maker = async_sessionmaker(
            async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        # Session 1: Change settings
        async with session_maker() as session1:
            settings_repo1 = UserSettingsRepositorySQLAlchemy(
                session1, TEST_USER_CONTEXT
            )
            settings = await settings_repo1.get_or_create()
            settings.update_sync(auto_post_transactions=True, default_currency="CHF")
            settings.update_display(
                show_draft_transactions=False, default_date_range_days=60
            )
            await settings_repo1.save(settings)
            await session1.commit()

        # Session 2: Verify settings persisted
        async with session_maker() as session2:
            settings_repo2 = UserSettingsRepositorySQLAlchemy(
                session2, TEST_USER_CONTEXT
            )
            settings = await settings_repo2.find()
            assert settings is not None

            assert settings.sync.auto_post_transactions is True
            assert settings.sync.default_currency == "CHF"
            assert settings.display.show_draft_transactions is False
            assert settings.display.default_date_range_days == 60

    @pytest.mark.asyncio
    async def test_multiple_preference_updates_are_cumulative(
        self,
        db_session,
        user_repo,
        settings_repo,
    ):
        """Multiple partial updates accumulate correctly."""
        await setup_test_user(user_repo, db_session)

        settings = await settings_repo.get_or_create()

        # First update: just auto_post
        settings.update_sync(auto_post_transactions=True)
        await settings_repo.save(settings)
        await db_session.flush()

        settings = await settings_repo.find()
        assert settings.sync.auto_post_transactions is True
        assert settings.display.show_draft_transactions is True  # Default

        # Second update: just show_drafts
        settings.update_display(show_draft_transactions=False)
        await settings_repo.save(settings)
        await db_session.flush()

        settings = await settings_repo.find()
        # Both should reflect their updates
        assert settings.sync.auto_post_transactions is True
        assert settings.display.show_draft_transactions is False

        # Third update: just currency
        settings.update_sync(default_currency="GBP")
        await settings_repo.save(settings)
        await db_session.flush()

        settings = await settings_repo.find()
        assert settings.sync.auto_post_transactions is True
        assert settings.sync.default_currency == "GBP"
        assert settings.display.show_draft_transactions is False
