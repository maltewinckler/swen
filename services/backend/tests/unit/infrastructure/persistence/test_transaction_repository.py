"""
Unit tests for TransactionRepositorySQLAlchemy.

These tests verify the persistence layer for accounting transactions.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money
from swen.infrastructure.persistence.sqlalchemy.models import (
    JournalEntryModel,
)
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from tests.unit.infrastructure.persistence.conftest import TEST_USER_ID


class TestTransactionRepositorySQLAlchemy:
    """Test suite for accounting transaction repository."""

    @pytest.fixture
    async def setup_accounts(self, async_session, current_user):
        """Set up test accounts."""
        account_repo = AccountRepositorySQLAlchemy(async_session, current_user)

        checking = Account("Checking Account", AccountType.ASSET, "1000", TEST_USER_ID)
        expense = Account("Office Supplies", AccountType.EXPENSE, "5000", TEST_USER_ID)

        await account_repo.save(checking)
        await account_repo.save(expense)

        return {"checking": checking, "expense": expense, "repo": account_repo, "current_user": current_user}

    @pytest.mark.asyncio
    async def test_save_new_transaction(self, async_session, setup_accounts):
        """Test saving a new transaction."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        transaction = Transaction(
            description="Office supplies purchase",
            user_id=TEST_USER_ID,
            counterparty="Office Depot",
        )
        transaction.add_debit(accounts["expense"], Money(Decimal("50.00")))
        transaction.add_credit(accounts["checking"], Money(Decimal("50.00")))

        # Act
        await transaction_repo.save(transaction)

        # Assert
        retrieved = await transaction_repo.find_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.description == "Office supplies purchase"
        assert retrieved.counterparty == "Office Depot"
        assert len(retrieved.entries) == 2

    @pytest.mark.asyncio
    async def test_save_updates_existing_transaction(
        self,
        async_session,
        setup_accounts,
    ):
        """Test that saving an existing transaction updates it."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        transaction = Transaction("Test Transaction", TEST_USER_ID)
        transaction.add_debit(accounts["expense"], Money(Decimal("100.00")))
        transaction.add_credit(accounts["checking"], Money(Decimal("100.00")))
        await transaction_repo.save(transaction)

        # Act - modify and save again
        transaction.post()
        await transaction_repo.save(transaction)

        # Assert
        retrieved = await transaction_repo.find_by_id(transaction.id)
        assert retrieved is not None
        assert retrieved.is_posted is True

    @pytest.mark.asyncio
    async def test_find_by_counterparty(self, async_session, setup_accounts):
        """Test finding transactions by counterparty."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        # Create transactions with different counterparties
        tx1 = Transaction("Purchase 1", TEST_USER_ID, counterparty="Amazon")
        tx1.add_debit(accounts["expense"], Money(Decimal("30.00")))
        tx1.add_credit(accounts["checking"], Money(Decimal("30.00")))
        await transaction_repo.save(tx1)

        tx2 = Transaction("Purchase 2", TEST_USER_ID, counterparty="Amazon")
        tx2.add_debit(accounts["expense"], Money(Decimal("40.00")))
        tx2.add_credit(accounts["checking"], Money(Decimal("40.00")))
        await transaction_repo.save(tx2)

        tx3 = Transaction("Purchase 3", TEST_USER_ID, counterparty="eBay")
        tx3.add_debit(accounts["expense"], Money(Decimal("20.00")))
        tx3.add_credit(accounts["checking"], Money(Decimal("20.00")))
        await transaction_repo.save(tx3)

        # Act
        amazon_txs = await transaction_repo.find_by_counterparty("Amazon")

        # Assert
        assert len(amazon_txs) == 2
        descriptions = {tx.description for tx in amazon_txs}
        assert descriptions == {"Purchase 1", "Purchase 2"}

    @pytest.mark.asyncio
    async def test_find_by_counterparty_iban(self, async_session, setup_accounts):
        """Test finding transactions by counterparty IBAN."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        transaction = Transaction(
            "Test",
            TEST_USER_ID,
            counterparty_iban="DE89370400440532013000",
        )
        transaction.add_debit(accounts["expense"], Money(Decimal("75.00")))
        transaction.add_credit(accounts["checking"], Money(Decimal("75.00")))
        await transaction_repo.save(transaction)

        # Act
        retrieved_list = await transaction_repo.find_by_counterparty_iban(
            "DE89370400440532013000",
        )

        # Assert
        assert len(retrieved_list) == 1
        assert retrieved_list[0].id == transaction.id
        assert retrieved_list[0].counterparty_iban == "DE89370400440532013000"

    @pytest.mark.asyncio
    async def test_find_posted_transactions(self, async_session, setup_accounts):
        """Test finding only posted transactions."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        # Create posted and draft transactions
        posted = Transaction("Posted Transaction", TEST_USER_ID)
        posted.add_debit(accounts["expense"], Money(Decimal("100.00")))
        posted.add_credit(accounts["checking"], Money(Decimal("100.00")))
        posted.post()
        await transaction_repo.save(posted)

        draft = Transaction("Draft Transaction", TEST_USER_ID)
        draft.add_debit(accounts["expense"], Money(Decimal("50.00")))
        draft.add_credit(accounts["checking"], Money(Decimal("50.00")))
        await transaction_repo.save(draft)

        # Act
        posted_txs = await transaction_repo.find_posted_transactions()

        # Assert
        assert len(posted_txs) == 1
        assert posted_txs[0].description == "Posted Transaction"
        assert posted_txs[0].is_posted is True

    @pytest.mark.asyncio
    async def test_find_draft_transactions(self, async_session, setup_accounts):
        """Test finding only draft transactions."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        # Create posted and draft transactions
        posted = Transaction("Posted Transaction", TEST_USER_ID)
        posted.add_debit(accounts["expense"], Money(Decimal("100.00")))
        posted.add_credit(accounts["checking"], Money(Decimal("100.00")))
        posted.post()
        await transaction_repo.save(posted)

        draft = Transaction("Draft Transaction", TEST_USER_ID)
        draft.add_debit(accounts["expense"], Money(Decimal("50.00")))
        draft.add_credit(accounts["checking"], Money(Decimal("50.00")))
        await transaction_repo.save(draft)

        # Act
        draft_txs = await transaction_repo.find_draft_transactions()

        # Assert
        assert len(draft_txs) == 1
        assert draft_txs[0].description == "Draft Transaction"
        assert draft_txs[0].is_posted is False

    @pytest.mark.asyncio
    async def test_find_by_account(self, async_session, setup_accounts):
        """Test finding transactions involving a specific account."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        # Create transaction involving checking account
        tx1 = Transaction("Transaction 1", TEST_USER_ID)
        tx1.add_debit(accounts["expense"], Money(Decimal("100.00")))
        tx1.add_credit(accounts["checking"], Money(Decimal("100.00")))
        await transaction_repo.save(tx1)

        # Create another account and transaction not involving checking
        other_account = Account("Other Account", AccountType.EXPENSE, "5001", TEST_USER_ID)
        await account_repo.save(other_account)

        tx2 = Transaction("Transaction 2", TEST_USER_ID)
        tx2.add_debit(other_account, Money(Decimal("50.00")))
        tx2.add_credit(accounts["checking"], Money(Decimal("50.00")))
        await transaction_repo.save(tx2)

        # Act
        checking_txs = await transaction_repo.find_by_account(
            accounts["checking"].id,
        )

        # Assert - both transactions involve checking account
        assert len(checking_txs) == 2

    @pytest.mark.asyncio
    async def test_delete_transaction(self, async_session, setup_accounts):
        """Test deleting a transaction."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        transaction = Transaction("To Delete", TEST_USER_ID)
        transaction.add_debit(accounts["expense"], Money(Decimal("25.00")))
        transaction.add_credit(accounts["checking"], Money(Decimal("25.00")))
        await transaction_repo.save(transaction)

        # Act
        await transaction_repo.delete(transaction.id)

        # Assert
        retrieved = await transaction_repo.find_by_id(transaction.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_transaction_with_metadata(self, async_session, setup_accounts):
        """Test saving and retrieving transaction with metadata."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        transaction = Transaction(
            "Test Transaction",
            user_id=TEST_USER_ID,
            metadata={"category": "office", "project": "Q4-2025"},
        )
        transaction.add_debit(accounts["expense"], Money(Decimal("150.00")))
        transaction.add_credit(accounts["checking"], Money(Decimal("150.00")))
        await transaction_repo.save(transaction)

        # Act
        retrieved = await transaction_repo.find_by_id(transaction.id)

        # Assert
        assert retrieved is not None
        # Note: 'source' is always present (synced from first-class field)
        assert retrieved.metadata_raw == {
            "category": "office",
            "project": "Q4-2025",
            "source": "manual",  # Default source
        }

    @pytest.mark.asyncio
    async def test_transaction_preserves_entry_currency(
        self,
        async_session,
        setup_accounts,
    ):
        """Ensure stored transactions keep their currency when rehydrated."""
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        usd_amount = Money(Decimal("75.00"), Currency("USD"))
        transaction = Transaction("USD Purchase", TEST_USER_ID)
        transaction.add_debit(accounts["expense"], usd_amount)
        transaction.add_credit(accounts["checking"], usd_amount)

        await transaction_repo.save(transaction)

        retrieved = await transaction_repo.find_by_id(transaction.id)

        assert retrieved is not None
        assert all(
            entry.amount.currency == Currency("USD") for entry in retrieved.entries
        )

    @pytest.mark.asyncio
    async def test_journal_entries_cascade_delete(
        self,
        async_session,
        setup_accounts,
    ):
        """Test that deleting transaction cascades to journal entries."""
        # Arrange
        accounts = setup_accounts
        account_repo = accounts["repo"]
        current_user = accounts["current_user"]
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session,
            account_repo,
            current_user,
        )

        transaction = Transaction("Cascade Test", TEST_USER_ID)
        transaction.add_debit(accounts["expense"], Money(Decimal("100.00")))
        transaction.add_credit(accounts["checking"], Money(Decimal("100.00")))
        await transaction_repo.save(transaction)

        # Verify entries exist
        stmt = select(JournalEntryModel).where(
            JournalEntryModel.transaction_id == transaction.id,
        )
        result = await async_session.execute(stmt)
        entries_before = result.scalars().all()
        assert len(entries_before) == 2

        # Act - delete transaction
        await transaction_repo.delete(transaction.id)

        # Assert - entries should be deleted too
        result = await async_session.execute(stmt)
        entries_after = result.scalars().all()
        assert len(entries_after) == 0


class TestJournalEntryDataIntegrity:
    """Tests for journal entry data integrity constraints and validation."""

    @pytest.fixture
    async def setup_test_data(self, async_session, current_user):
        """Set up test accounts and transaction."""
        from datetime import datetime, timezone
        from uuid import uuid4

        from swen.infrastructure.persistence.sqlalchemy.models import (
            AccountModel,
            TransactionModel,
        )

        # Create accounts directly in DB
        checking_id = uuid4()
        expense_id = uuid4()

        async_session.add(
            AccountModel(
                id=checking_id,
                user_id=TEST_USER_ID,
                name="Checking",
                account_type="asset",
                account_number="1000",
                default_currency="EUR",
                is_active=True,
                created_at=datetime.now(tz=timezone.utc),
            ),
        )
        async_session.add(
            AccountModel(
                id=expense_id,
                user_id=TEST_USER_ID,
                name="Expense",
                account_type="expense",
                account_number="5000",
                default_currency="EUR",
                is_active=True,
                created_at=datetime.now(tz=timezone.utc),
            ),
        )

        # Create transaction
        tx_id = uuid4()
        async_session.add(
            TransactionModel(
                id=tx_id,
                user_id=TEST_USER_ID,
                description="Test Transaction",
                date=datetime.now(tz=timezone.utc),
                is_posted=False,
                created_at=datetime.now(tz=timezone.utc),
            ),
        )
        await async_session.flush()

        return {
            "checking_id": checking_id,
            "expense_id": expense_id,
            "tx_id": tx_id,
            "current_user": current_user,
        }

    @pytest.mark.asyncio
    async def test_db_constraint_rejects_both_debit_and_credit_positive(
        self,
        async_session,
        setup_test_data,
    ):
        """Test that DB constraint prevents entries with both debit and credit positive."""
        from uuid import uuid4

        from sqlalchemy.exc import IntegrityError

        setup = setup_test_data

        # Attempt to create invalid entry with both debit and credit positive
        invalid_entry = JournalEntryModel(
            id=uuid4(),
            transaction_id=setup["tx_id"],
            account_id=setup["checking_id"],
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("50.00"),  # INVALID: both positive
            currency="EUR",
        )
        async_session.add(invalid_entry)

        # Assert - DB constraint should reject this
        with pytest.raises(IntegrityError) as exc_info:
            await async_session.flush()

        assert "ck_journal_entry_xor_debit_credit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_db_constraint_rejects_both_zero(
        self,
        async_session,
        setup_test_data,
    ):
        """Test that DB constraint prevents entries with both debit and credit zero."""
        from uuid import uuid4

        from sqlalchemy.exc import IntegrityError

        setup = setup_test_data

        # Attempt to create invalid entry with both zero
        invalid_entry = JournalEntryModel(
            id=uuid4(),
            transaction_id=setup["tx_id"],
            account_id=setup["checking_id"],
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("0.00"),  # INVALID: both zero
            currency="EUR",
        )
        async_session.add(invalid_entry)

        # Assert - DB constraint should reject this
        with pytest.raises(IntegrityError) as exc_info:
            await async_session.flush()

        assert "ck_journal_entry_xor_debit_credit" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_db_allows_valid_debit_entry(
        self,
        async_session,
        setup_test_data,
    ):
        """Test that DB accepts valid debit entries (debit > 0, credit = 0)."""
        from uuid import uuid4

        setup = setup_test_data

        valid_entry = JournalEntryModel(
            id=uuid4(),
            transaction_id=setup["tx_id"],
            account_id=setup["expense_id"],
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("0.00"),
            currency="EUR",
        )
        async_session.add(valid_entry)

        # Should not raise
        await async_session.flush()

        # Verify it's saved
        result = await async_session.execute(
            select(JournalEntryModel).where(
                JournalEntryModel.id == valid_entry.id,
            ),
        )
        saved = result.scalar_one_or_none()
        assert saved is not None
        assert saved.debit_amount == Decimal("100.00")
        assert saved.credit_amount == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_db_allows_valid_credit_entry(
        self,
        async_session,
        setup_test_data,
    ):
        """Test that DB accepts valid credit entries (debit = 0, credit > 0)."""
        from uuid import uuid4

        setup = setup_test_data

        valid_entry = JournalEntryModel(
            id=uuid4(),
            transaction_id=setup["tx_id"],
            account_id=setup["checking_id"],
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("100.00"),
            currency="EUR",
        )
        async_session.add(valid_entry)

        # Should not raise
        await async_session.flush()

        # Verify it's saved
        result = await async_session.execute(
            select(JournalEntryModel).where(
                JournalEntryModel.id == valid_entry.id,
            ),
        )
        saved = result.scalar_one_or_none()
        assert saved is not None
        assert saved.debit_amount == Decimal("0.00")
        assert saved.credit_amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_valid_entries_are_reconstituted_correctly(
        self,
        async_session,
        setup_test_data,
    ):
        """Test that valid entries are reconstituted without errors."""
        from uuid import uuid4

        setup = setup_test_data

        # Create valid debit entry
        valid_debit = JournalEntryModel(
            id=uuid4(),
            transaction_id=setup["tx_id"],
            account_id=setup["expense_id"],
            debit_amount=Decimal("100.00"),
            credit_amount=Decimal("0.00"),
            currency="EUR",
        )
        # Create valid credit entry
        valid_credit = JournalEntryModel(
            id=uuid4(),
            transaction_id=setup["tx_id"],
            account_id=setup["checking_id"],
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("100.00"),
            currency="EUR",
        )
        async_session.add_all([valid_debit, valid_credit])
        await async_session.flush()

        # Set up repository
        account_repo = AccountRepositorySQLAlchemy(
            async_session, setup["current_user"],
        )
        transaction_repo = TransactionRepositorySQLAlchemy(
            async_session, account_repo, setup["current_user"],
        )

        # Act
        transaction = await transaction_repo.find_by_id(setup["tx_id"])

        # Assert
        assert transaction is not None
        assert len(transaction.entries) == 2

        debit_entries = [e for e in transaction.entries if e.is_debit()]
        credit_entries = [e for e in transaction.entries if e.is_credit()]
        assert len(debit_entries) == 1
        assert len(credit_entries) == 1
        assert debit_entries[0].debit.amount == Decimal("100.00")
        assert credit_entries[0].credit.amount == Decimal("100.00")
