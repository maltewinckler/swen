"""
Security tests for multi-user data isolation.

These tests verify that users cannot access each other's data.

CURRENT STATUS:
- Credentials: Full isolation implemented and tested
- Accounts: Repositories scope queries by user_id
- Transactions: Repositories scope queries by user_id
- Mappings: Repositories scope queries by user_id
- User Preferences: Isolated by user entity

NOTE: This test file documents isolation guarantees and regression tests
that ensure repositories keep enforcing user-level scoping.
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from swen.application.context import UserContext
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency, Money
from swen.domain.banking.value_objects import BankCredentials
from swen.domain.integration.entities import AccountMapping
from swen.domain.user import User
from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankCredentialRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.security import (
    StoredBankCredentialsRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.user import (
    UserRepositorySQLAlchemy,
)
from swen.infrastructure.security.encryption_service_fernet import (
    FernetEncryptionService,
)

# Two distinct test users
USER_ALICE = User.create("alice@example.com")
USER_BOB = User.create("bob@example.com")

# User contexts for repository scoping
ALICE_CONTEXT = UserContext(user_id=USER_ALICE.id, email="alice@example.com")
BOB_CONTEXT = UserContext(user_id=USER_BOB.id, email="bob@example.com")


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture(scope="module")
def isolation_engine():
    """Create async engine for isolation tests."""
    return create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )


@pytest_asyncio.fixture(scope="function")
async def isolation_session(isolation_engine):
    """Create fresh database session for each test."""
    async with isolation_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = async_sessionmaker(
        isolation_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    async with isolation_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def encryption_service():
    """Create encryption service for credential tests."""
    test_key = Fernet.generate_key()  # Returns bytes
    return FernetEncryptionService(test_key)


# ============================================================================
# Credential Isolation Tests (WORKING)
# ============================================================================


class TestCredentialIsolation:
    """Test that bank credentials are isolated by user.

    This is fully implemented and working correctly.
    """

    @pytest.mark.asyncio
    async def test_users_cannot_access_each_others_credentials(
        self,
        isolation_session,
        encryption_service,
    ):
        """Critical: Users must not be able to access other users' credentials."""
        # Arrange - create user-scoped repositories for each user
        alice_stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        alice_credential_repo = BankCredentialRepositorySQLAlchemy(
            alice_stored_repo,
            encryption_service,
            ALICE_CONTEXT,
        )

        bob_stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
            isolation_session,
            BOB_CONTEXT,
        )
        bob_credential_repo = BankCredentialRepositorySQLAlchemy(
            bob_stored_repo,
            encryption_service,
            BOB_CONTEXT,
        )

        alice_creds = BankCredentials.from_plain(
            blz="50031000",
            username="alice_bank_user",
            pin="alice_secret_pin",
            endpoint="https://banking.example.com",
        )

        bob_creds = BankCredentials.from_plain(
            blz="50031000",  # Same bank
            username="bob_bank_user",
            pin="bob_secret_pin",
            endpoint="https://banking.example.com",
        )

        await alice_credential_repo.save(alice_creds, label="Alice's Bank")
        await bob_credential_repo.save(bob_creds, label="Bob's Bank")
        await isolation_session.commit()

        # Act - Each user queries for credentials via their own user-scoped repository
        alice_retrieved = await alice_credential_repo.find_by_blz("50031000")
        bob_retrieved = await bob_credential_repo.find_by_blz("50031000")

        # Assert - Each user only gets their own credentials
        assert alice_retrieved is not None
        assert alice_retrieved.username.get_value() == "alice_bank_user"
        assert alice_retrieved.pin.get_value() == "alice_secret_pin"

        assert bob_retrieved is not None
        assert bob_retrieved.username.get_value() == "bob_bank_user"
        assert bob_retrieved.pin.get_value() == "bob_secret_pin"

    @pytest.mark.asyncio
    async def test_find_all_by_user_returns_only_own_credentials(
        self,
        isolation_session,
        encryption_service,
    ):
        """Users only see their own credentials in list."""
        # Arrange - create user-scoped repositories for each user
        alice_stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        alice_credential_repo = BankCredentialRepositorySQLAlchemy(
            alice_stored_repo,
            encryption_service,
            ALICE_CONTEXT,
        )

        bob_stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
            isolation_session,
            BOB_CONTEXT,
        )
        bob_credential_repo = BankCredentialRepositorySQLAlchemy(
            bob_stored_repo,
            encryption_service,
            BOB_CONTEXT,
        )

        alice_creds = BankCredentials.from_plain(
            blz="50031000",
            username="alice_user",
            pin="alice_pin",
            endpoint="https://banking.example.com",
        )

        bob_creds = BankCredentials.from_plain(
            blz="12345678",
            username="bob_user",
            pin="bob_pin",
            endpoint="https://banking.example.com",
        )

        await alice_credential_repo.save(alice_creds, label="Alice's Bank")
        await bob_credential_repo.save(bob_creds, label="Bob's Bank")
        await isolation_session.commit()

        # Act - Each user queries via their own user-scoped repository
        alice_list = await alice_credential_repo.find_all()
        bob_list = await bob_credential_repo.find_all()

        # Assert - Each user only sees their own
        assert len(alice_list) == 1
        assert alice_list[0][2] == "Alice's Bank"  # (id, blz, label)

        assert len(bob_list) == 1
        assert bob_list[0][2] == "Bob's Bank"

    @pytest.mark.asyncio
    async def test_credential_deletion_only_affects_own_credentials(
        self,
        isolation_session,
        encryption_service,
    ):
        """Deleting credentials should only affect the user's own credentials."""
        # Arrange - create user-scoped repositories for each user
        alice_stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        alice_credential_repo = BankCredentialRepositorySQLAlchemy(
            alice_stored_repo,
            encryption_service,
            ALICE_CONTEXT,
        )

        bob_stored_repo = StoredBankCredentialsRepositorySQLAlchemy(
            isolation_session,
            BOB_CONTEXT,
        )
        bob_credential_repo = BankCredentialRepositorySQLAlchemy(
            bob_stored_repo,
            encryption_service,
            BOB_CONTEXT,
        )

        alice_creds = BankCredentials.from_plain(
            blz="50031000",
            username="alice_user",
            pin="alice_pin",
            endpoint="https://banking.example.com",
        )

        bob_creds = BankCredentials.from_plain(
            blz="50031000",
            username="bob_user",
            pin="bob_pin",
            endpoint="https://banking.example.com",
        )

        await alice_credential_repo.save(alice_creds)
        await bob_credential_repo.save(bob_creds)
        await isolation_session.commit()

        # Act - Alice deletes her credentials via her user-scoped repository
        deleted = await alice_credential_repo.delete("50031000")
        await isolation_session.commit()

        # Assert - Alice's credentials are gone
        assert deleted is True
        alice_retrieved = await alice_credential_repo.find_by_blz("50031000")
        assert alice_retrieved is None

        # Assert - Bob's credentials are unaffected
        bob_retrieved = await bob_credential_repo.find_by_blz("50031000")
        assert bob_retrieved is not None
        assert bob_retrieved.username.get_value() == "bob_user"


# ============================================================================
# User Preferences Isolation Tests (WORKING)
# ============================================================================


class TestUserPreferencesIsolation:
    """Test that user preferences are isolated."""

    @pytest.mark.asyncio
    async def test_preferences_are_user_specific(self, isolation_session):
        """Each user should have independent preferences."""
        # Arrange
        user_repo = UserRepositorySQLAlchemy(isolation_session)

        alice = User.create("alice-prefs@example.com")
        alice.update_preferences(auto_post_transactions=True)

        bob = User.create("bob-prefs@example.com")
        bob.update_preferences(auto_post_transactions=False)

        await user_repo.save(alice)
        await user_repo.save(bob)
        await isolation_session.commit()

        # Act
        alice_retrieved = await user_repo.find_by_id(alice.id)
        bob_retrieved = await user_repo.find_by_id(bob.id)

        # Assert
        assert alice_retrieved is not None
        assert bob_retrieved is not None
        assert alice_retrieved.preferences.sync_settings.auto_post_transactions is True
        assert bob_retrieved.preferences.sync_settings.auto_post_transactions is False

    @pytest.mark.asyncio
    async def test_changing_preferences_doesnt_affect_others(self, isolation_session):
        """Updating one user's preferences should not affect other users."""
        # Arrange
        user_repo = UserRepositorySQLAlchemy(isolation_session)

        alice = User.create("alice-update@example.com")
        bob = User.create("bob-update@example.com")

        await user_repo.save(alice)
        await user_repo.save(bob)
        await isolation_session.commit()

        # Act - Alice changes her preferences
        alice_fresh = await user_repo.find_by_id(alice.id)
        assert alice_fresh is not None
        alice_fresh.update_preferences(
            show_draft_transactions=False,
            default_date_range_days=7,  # Different from default (30)
        )
        await user_repo.save(alice_fresh)
        await isolation_session.commit()

        # Assert - Bob's preferences unchanged (should still be defaults)
        bob_fresh = await user_repo.find_by_id(bob.id)
        assert bob_fresh is not None
        assert bob_fresh.preferences.display_settings.show_draft_transactions is True
        assert bob_fresh.preferences.display_settings.default_date_range_days == 30

        # Verify Alice's were actually changed
        alice_check = await user_repo.find_by_id(alice.id)
        assert alice_check is not None
        assert alice_check.preferences.display_settings.show_draft_transactions is False
        assert alice_check.preferences.display_settings.default_date_range_days == 7


# ============================================================================
# Entity user_id Storage Tests
#
# These tests verify that user_id metadata is correctly persisted on entities.
# ============================================================================


class TestAccountUserIdStorage:
    """Test that accounts correctly store user_id."""

    @pytest.mark.asyncio
    async def test_account_stores_user_id(self, isolation_session):
        """Accounts should correctly store their user_id."""
        # Arrange - create user-scoped repositories for each user
        alice_account_repo = AccountRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        bob_account_repo = AccountRepositorySQLAlchemy(isolation_session, BOB_CONTEXT)

        alice_account = Account(
            name="Alice's Checking",
            account_type=AccountType.ASSET,
            account_number="ALICE-001",
            default_currency=Currency("EUR"),
            user_id=USER_ALICE.id,
        )

        bob_account = Account(
            name="Bob's Savings",
            account_type=AccountType.ASSET,
            account_number="BOB-001",
            default_currency=Currency("EUR"),
            user_id=USER_BOB.id,
        )

        await alice_account_repo.save(alice_account)
        await bob_account_repo.save(bob_account)
        await isolation_session.commit()

        # Act - each user retrieves via their own user-scoped repository
        alice_retrieved = await alice_account_repo.find_by_id(alice_account.id)
        bob_retrieved = await bob_account_repo.find_by_id(bob_account.id)

        # Assert - user_id is correctly stored
        assert alice_retrieved is not None
        assert bob_retrieved is not None
        assert alice_retrieved.user_id == USER_ALICE.id
        assert bob_retrieved.user_id == USER_BOB.id


class TestTransactionUserIdStorage:
    """Test that transactions correctly store user_id."""

    @pytest.mark.asyncio
    async def test_transaction_stores_user_id(self, isolation_session):
        """Transactions should correctly store their user_id."""
        # Arrange - create user-scoped repositories for each user
        alice_account_repo = AccountRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        alice_transaction_repo = TransactionRepositorySQLAlchemy(
            isolation_session,
            alice_account_repo,
            ALICE_CONTEXT,
        )

        bob_account_repo = AccountRepositorySQLAlchemy(isolation_session, BOB_CONTEXT)
        bob_transaction_repo = TransactionRepositorySQLAlchemy(
            isolation_session,
            bob_account_repo,
            BOB_CONTEXT,
        )

        alice_txn = Transaction(
            description="Alice's Transaction",
            date=datetime.now(tz=timezone.utc),
            user_id=USER_ALICE.id,
        )

        bob_txn = Transaction(
            description="Bob's Transaction",
            date=datetime.now(tz=timezone.utc),
            user_id=USER_BOB.id,
        )

        await alice_transaction_repo.save(alice_txn)
        await bob_transaction_repo.save(bob_txn)
        await isolation_session.commit()

        # Act - each user retrieves via their own user-scoped repository
        alice_retrieved = await alice_transaction_repo.find_by_id(alice_txn.id)
        bob_retrieved = await bob_transaction_repo.find_by_id(bob_txn.id)

        # Assert - user_id is correctly stored
        assert alice_retrieved is not None
        assert bob_retrieved is not None
        assert alice_retrieved.user_id == USER_ALICE.id
        assert bob_retrieved.user_id == USER_BOB.id


class TestAccountMappingUserIdStorage:
    """Test that account mappings correctly store user_id."""

    @pytest.mark.asyncio
    async def test_mapping_stores_user_id(self, isolation_session):
        """Account mappings should correctly store their user_id."""
        # Arrange - create user-scoped repositories for each user
        alice_mapping_repo = AccountMappingRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        alice_account_repo = AccountRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )

        bob_mapping_repo = AccountMappingRepositorySQLAlchemy(
            isolation_session,
            BOB_CONTEXT,
        )
        bob_account_repo = AccountRepositorySQLAlchemy(isolation_session, BOB_CONTEXT)

        # Create accounts first
        alice_account = Account(
            name="Alice Account",
            account_type=AccountType.ASSET,
            account_number="ALICE-MAP",
            user_id=USER_ALICE.id,
        )
        bob_account = Account(
            name="Bob Account",
            account_type=AccountType.ASSET,
            account_number="BOB-MAP",
            user_id=USER_BOB.id,
        )

        await alice_account_repo.save(alice_account)
        await bob_account_repo.save(bob_account)

        # Create mappings
        alice_mapping = AccountMapping(
            iban="DE11111111111111111111",
            accounting_account_id=alice_account.id,
            account_name="Alice Bank",
            user_id=USER_ALICE.id,
        )

        bob_mapping = AccountMapping(
            iban="DE22222222222222222222",
            accounting_account_id=bob_account.id,
            account_name="Bob Bank",
            user_id=USER_BOB.id,
        )

        await alice_mapping_repo.save(alice_mapping)
        await bob_mapping_repo.save(bob_mapping)
        await isolation_session.commit()

        # Act - each user retrieves via their own user-scoped repository
        alice_retrieved = await alice_mapping_repo.find_by_id(alice_mapping.id)
        bob_retrieved = await bob_mapping_repo.find_by_id(bob_mapping.id)

        # Assert - user_id is correctly stored
        assert alice_retrieved is not None
        assert bob_retrieved is not None
        assert alice_retrieved.user_id == USER_ALICE.id
        assert bob_retrieved.user_id == USER_BOB.id


# ============================================================================
# Repository-Level Filtering Guards
#
# Regression tests asserting that repository queries enforce user_id scoping.
# ============================================================================


class TestRepositoryFilteringGuards:
    """Ensure repository-level user_id scoping prevents cross-tenant access."""

    @pytest.mark.asyncio
    async def test_account_find_all_should_filter_by_user(self, isolation_session):
        """AccountRepository.find_all returns only the current user's accounts."""
        alice_repo = AccountRepositorySQLAlchemy(isolation_session, ALICE_CONTEXT)
        bob_repo = AccountRepositorySQLAlchemy(isolation_session, BOB_CONTEXT)

        alice_account = Account(
            name="Alice Asset",
            account_type=AccountType.ASSET,
            account_number="ALICE-ACC-001",
            user_id=USER_ALICE.id,
            default_currency=Currency("EUR"),
        )
        bob_account = Account(
            name="Bob Asset",
            account_type=AccountType.ASSET,
            account_number="BOB-ACC-001",
            user_id=USER_BOB.id,
            default_currency=Currency("EUR"),
        )

        await alice_repo.save(alice_account)
        await bob_repo.save(bob_account)
        await isolation_session.commit()

        alice_accounts = await alice_repo.find_all()
        bob_accounts = await bob_repo.find_all()

        assert [acct.id for acct in alice_accounts] == [alice_account.id]
        assert [acct.id for acct in bob_accounts] == [bob_account.id]
        assert await alice_repo.find_by_id(bob_account.id) is None
        assert await bob_repo.find_by_id(alice_account.id) is None

    @pytest.mark.asyncio
    async def test_transaction_find_all_should_filter_by_user(self, isolation_session):
        """
        TransactionRepository.find_all returns only the current user's transactions.
        """
        alice_account_repo = AccountRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        bob_account_repo = AccountRepositorySQLAlchemy(isolation_session, BOB_CONTEXT)

        alice_transaction_repo = TransactionRepositorySQLAlchemy(
            isolation_session,
            alice_account_repo,
            ALICE_CONTEXT,
        )
        bob_transaction_repo = TransactionRepositorySQLAlchemy(
            isolation_session,
            bob_account_repo,
            BOB_CONTEXT,
        )

        # Accounts used in transactions
        alice_asset = Account(
            name="Alice Cash",
            account_type=AccountType.ASSET,
            account_number="ALICE-TXN-ASSET",
            user_id=USER_ALICE.id,
            default_currency=Currency("EUR"),
        )
        alice_income = Account(
            name="Alice Income",
            account_type=AccountType.INCOME,
            account_number="ALICE-TXN-INCOME",
            user_id=USER_ALICE.id,
            default_currency=Currency("EUR"),
        )
        bob_asset = Account(
            name="Bob Cash",
            account_type=AccountType.ASSET,
            account_number="BOB-TXN-ASSET",
            user_id=USER_BOB.id,
            default_currency=Currency("EUR"),
        )
        bob_income = Account(
            name="Bob Income",
            account_type=AccountType.INCOME,
            account_number="BOB-TXN-INCOME",
            user_id=USER_BOB.id,
            default_currency=Currency("EUR"),
        )

        await alice_account_repo.save(alice_asset)
        await alice_account_repo.save(alice_income)
        await bob_account_repo.save(bob_asset)
        await bob_account_repo.save(bob_income)

        amount = Money(Decimal("100.00"), Currency("EUR"))

        alice_txn = Transaction(description="Alice Sale", user_id=USER_ALICE.id)
        alice_txn.add_debit(alice_asset, amount)
        alice_txn.add_credit(alice_income, amount)

        bob_txn = Transaction(description="Bob Sale", user_id=USER_BOB.id)
        bob_txn.add_debit(bob_asset, amount)
        bob_txn.add_credit(bob_income, amount)

        await alice_transaction_repo.save(alice_txn)
        await bob_transaction_repo.save(bob_txn)
        await isolation_session.commit()

        alice_results = await alice_transaction_repo.find_all()
        bob_results = await bob_transaction_repo.find_all()

        assert len(alice_results) == 1
        assert len(bob_results) == 1
        assert alice_results[0].user_id == USER_ALICE.id
        assert bob_results[0].user_id == USER_BOB.id
        assert await alice_transaction_repo.find_by_id(bob_txn.id) is None
        assert await bob_transaction_repo.find_by_id(alice_txn.id) is None

    @pytest.mark.asyncio
    async def test_mapping_find_all_should_filter_by_user(self, isolation_session):
        """AccountMappingRepository.find_all returns only the current user's mappings"""
        alice_account_repo = AccountRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        bob_account_repo = AccountRepositorySQLAlchemy(isolation_session, BOB_CONTEXT)

        alice_mapping_repo = AccountMappingRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        bob_mapping_repo = AccountMappingRepositorySQLAlchemy(
            isolation_session,
            BOB_CONTEXT,
        )

        alice_account = Account(
            name="Alice Mapping Asset",
            account_type=AccountType.ASSET,
            account_number="ALICE-MAP-ASSET",
            user_id=USER_ALICE.id,
            default_currency=Currency("EUR"),
        )
        bob_account = Account(
            name="Bob Mapping Asset",
            account_type=AccountType.ASSET,
            account_number="BOB-MAP-ASSET",
            user_id=USER_BOB.id,
            default_currency=Currency("EUR"),
        )

        await alice_account_repo.save(alice_account)
        await bob_account_repo.save(bob_account)

        alice_mapping = AccountMapping(
            iban="DE11111111111111111111",
            accounting_account_id=alice_account.id,
            account_name="Alice Bank",
            user_id=USER_ALICE.id,
        )
        bob_mapping = AccountMapping(
            iban="DE22222222222222222222",
            accounting_account_id=bob_account.id,
            account_name="Bob Bank",
            user_id=USER_BOB.id,
        )

        await alice_mapping_repo.save(alice_mapping)
        await bob_mapping_repo.save(bob_mapping)
        await isolation_session.commit()

        alice_mappings = await alice_mapping_repo.find_all()
        bob_mappings = await bob_mapping_repo.find_all()

        assert [mapping.id for mapping in alice_mappings] == [alice_mapping.id]
        assert [mapping.id for mapping in bob_mappings] == [bob_mapping.id]
        assert await alice_mapping_repo.find_by_id(bob_mapping.id) is None
        assert await bob_mapping_repo.find_by_id(alice_mapping.id) is None

    @pytest.mark.asyncio
    async def test_find_by_id_should_verify_user_ownership(self, isolation_session):
        """find_by_id should return None for entities owned by other users."""
        alice_account_repo = AccountRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        bob_account_repo = AccountRepositorySQLAlchemy(isolation_session, BOB_CONTEXT)
        alice_mapping_repo = AccountMappingRepositorySQLAlchemy(
            isolation_session,
            ALICE_CONTEXT,
        )
        bob_mapping_repo = AccountMappingRepositorySQLAlchemy(
            isolation_session,
            BOB_CONTEXT,
        )

        alice_transaction_repo = TransactionRepositorySQLAlchemy(
            isolation_session,
            alice_account_repo,
            ALICE_CONTEXT,
        )
        bob_transaction_repo = TransactionRepositorySQLAlchemy(
            isolation_session,
            bob_account_repo,
            BOB_CONTEXT,
        )

        # Accounts for both users
        alice_asset = Account(
            name="Alice Guarded Asset",
            account_type=AccountType.ASSET,
            account_number="ALICE-GUARD-ASSET",
            user_id=USER_ALICE.id,
            default_currency=Currency("EUR"),
        )
        alice_income = Account(
            name="Alice Guarded Income",
            account_type=AccountType.INCOME,
            account_number="ALICE-GUARD-INCOME",
            user_id=USER_ALICE.id,
            default_currency=Currency("EUR"),
        )
        bob_asset = Account(
            name="Bob Guarded Asset",
            account_type=AccountType.ASSET,
            account_number="BOB-GUARD-ASSET",
            user_id=USER_BOB.id,
            default_currency=Currency("EUR"),
        )
        bob_income = Account(
            name="Bob Guarded Income",
            account_type=AccountType.INCOME,
            account_number="BOB-GUARD-INCOME",
            user_id=USER_BOB.id,
            default_currency=Currency("EUR"),
        )

        await alice_account_repo.save(alice_asset)
        await alice_account_repo.save(alice_income)
        await bob_account_repo.save(bob_asset)
        await bob_account_repo.save(bob_income)

        # Account mappings
        alice_mapping = AccountMapping(
            iban="DE33333333333333333333",
            accounting_account_id=alice_asset.id,
            account_name="Alice Guarded Map",
            user_id=USER_ALICE.id,
        )
        bob_mapping = AccountMapping(
            iban="DE44444444444444444444",
            accounting_account_id=bob_asset.id,
            account_name="Bob Guarded Map",
            user_id=USER_BOB.id,
        )

        await alice_mapping_repo.save(alice_mapping)
        await bob_mapping_repo.save(bob_mapping)

        # Transactions
        amount = Money(Decimal("50.00"), Currency("EUR"))

        alice_txn = Transaction(description="Alice Guarded Txn", user_id=USER_ALICE.id)
        alice_txn.add_debit(alice_asset, amount)
        alice_txn.add_credit(alice_income, amount)

        bob_txn = Transaction(description="Bob Guarded Txn", user_id=USER_BOB.id)
        bob_txn.add_debit(bob_asset, amount)
        bob_txn.add_credit(bob_income, amount)

        await alice_transaction_repo.save(alice_txn)
        await bob_transaction_repo.save(bob_txn)
        await isolation_session.commit()

        assert await alice_account_repo.find_by_id(bob_asset.id) is None
        assert await bob_account_repo.find_by_id(alice_asset.id) is None
        assert await alice_mapping_repo.find_by_id(bob_mapping.id) is None
        assert await bob_mapping_repo.find_by_id(alice_mapping.id) is None
        assert await alice_transaction_repo.find_by_id(bob_txn.id) is None
        assert await bob_transaction_repo.find_by_id(alice_txn.id) is None
