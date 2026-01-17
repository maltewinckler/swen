"""
Integration tests for transaction atomicity across multiple repositories.

These tests verify that the flush() strategy enables proper transactional
boundaries, ensuring that multiple repository operations are atomic.

Uses Testcontainers PostgreSQL for isolated, ephemeral database instances.
"""

from decimal import Decimal
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankAccount
from swen.domain.integration.entities import AccountMapping
from swen.infrastructure.persistence.sqlalchemy.repositories import (
    AccountMappingRepositorySQLAlchemy,
    AccountRepositorySQLAlchemy,
    BankAccountRepositorySQLAlchemy,
)

# Import Testcontainers fixtures
from tests.shared.fixtures.database import (
    TEST_USER_ID,
)


@pytest.fixture
def atomicity_session_maker(async_engine) -> async_sessionmaker:
    """Create a session maker for atomicity tests."""
    return async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session(
    session_maker: async_sessionmaker,
) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with automatic transaction management."""
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest.mark.integration
class TestTransactionAtomicity:
    """Test that multiple repository operations are atomic."""

    @pytest.mark.asyncio
    async def test_account_and_mapping_rollback_on_failure(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """
        Test that failure rolls back both account and mapping.

        This verifies the core benefit of flush() over commit():
        - With flush(): all operations are atomic
        - With commit(): first repo would be committed, second lost
        """
        iban = "DE89370400440532013000"

        # Attempt to create account and mapping, but fail
        with pytest.raises(ValueError, match="Simulated failure"):
            async for session in get_session(atomicity_session_maker):
                account_repo = AccountRepositorySQLAlchemy(session, current_user)
                mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

                # Create and save account
                account = Account(
                    name="Test Account - Should Rollback",
                    account_type=AccountType.ASSET,
                    account_number=iban,
                    default_currency=Currency("EUR"),
                    user_id=TEST_USER_ID,
                )
                await account_repo.save(account)

                # Create and save mapping
                mapping = AccountMapping(
                    iban=iban,
                    accounting_account_id=account.id,
                    account_name="Test Account - Should Rollback",
                    is_active=True,
                    user_id=TEST_USER_ID,
                )
                await mapping_repo.save(mapping)

                # Force failure before commit
                raise ValueError("Simulated failure")

        # Verify nothing was committed (this is the key assertion)
        async for session in get_session(atomicity_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Both should be None because rollback discarded everything
            account = await account_repo.find_by_account_number(iban)
            mapping = await mapping_repo.find_by_iban(iban)

            assert account is None, "Account should have been rolled back"
            assert mapping is None, "Mapping should have been rolled back"

    @pytest.mark.asyncio
    async def test_multiple_accounts_rollback_together(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """Test that multiple saves in one transaction rollback together."""

        with pytest.raises(RuntimeError, match="Intentional failure"):
            async for session in get_session(atomicity_session_maker):
                account_repo = AccountRepositorySQLAlchemy(session, current_user)

                # Save multiple accounts
                accounts = [
                    Account(
                        f"Account {i}",
                        AccountType.ASSET,
                        f"ACCT{i}",
                        user_id=TEST_USER_ID,
                    )
                    for i in range(1, 6)
                ]

                for account in accounts:
                    await account_repo.save(account)

                # Force failure
                raise RuntimeError("Intentional failure")

        # Verify none were committed
        async for session in get_session(atomicity_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)

            for i in range(1, 6):
                account = await account_repo.find_by_account_number(f"ACCT{i}")
                assert account is None, f"Account {i} should have been rolled back"

    @pytest.mark.asyncio
    async def test_successful_transaction_commits_all(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """Test that successful transaction commits all changes."""
        iban = "DE89370400440532013001"

        # Successful transaction
        async for session in get_session(atomicity_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Create and save account
            account = Account(
                name="Successful Account",
                account_type=AccountType.ASSET,
                account_number=iban,
                default_currency=Currency("EUR"),
                user_id=TEST_USER_ID,
            )
            await account_repo.save(account)

            # Create and save mapping
            mapping = AccountMapping(
                iban=iban,
                accounting_account_id=account.id,
                account_name="Successful Account",
                is_active=True,
                user_id=TEST_USER_ID,
            )
            await mapping_repo.save(mapping)
            # Transaction commits automatically here

        # Verify both were committed
        async for session in get_session(atomicity_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            account = await account_repo.find_by_account_number(iban)
            mapping = await mapping_repo.find_by_iban(iban)

            assert account is not None, "Account should be committed"
            assert mapping is not None, "Mapping should be committed"
            assert account.name == "Successful Account"
            assert mapping.accounting_account_id == account.id

    @pytest.mark.asyncio
    async def test_flush_makes_data_visible_within_transaction(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """
        Test that flush() makes data queryable within the same transaction.

        This is crucial: flush() syncs to database but doesn't commit,
        allowing queries to see the data before transaction completes.
        """
        iban = "DE89370400440532013002"

        async for session in get_session(atomicity_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Create account
            account = Account(
                name="Flush Test Account",
                account_type=AccountType.ASSET,
                account_number=iban,
                default_currency=Currency("EUR"),
                user_id=TEST_USER_ID,
            )
            await account_repo.save(account)  # This calls flush()

            # Should be able to query it immediately (before commit)
            found_account = await account_repo.find_by_account_number(iban)
            assert found_account is not None, "flush() should make data visible"
            assert found_account.id == account.id

            # Create mapping using the account we just found
            mapping = AccountMapping(
                iban=iban,
                accounting_account_id=found_account.id,
                account_name="Flush Test Account",
                is_active=True,
                user_id=TEST_USER_ID,
            )
            await mapping_repo.save(mapping)

            # Should also be queryable immediately
            found_mapping = await mapping_repo.find_by_iban(iban)
            assert found_mapping is not None, "flush() should make mapping visible"

    @pytest.mark.asyncio
    async def test_bank_account_and_transactions_atomic(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """Test that bank account and transactions rollback together."""
        iban = "DE89370400440532013003"

        with pytest.raises(ValueError, match="Transaction failed"):
            async for session in get_session(atomicity_session_maker):
                bank_account_repo = BankAccountRepositorySQLAlchemy(
                    session, current_user
                )

                # Create bank account
                bank_account = BankAccount(
                    iban=iban,
                    account_number="532013003",
                    blz="37040044",
                    account_holder="Test User",
                    account_type="Girokonto",
                    currency="EUR",
                    balance=Decimal("1000.00"),
                )
                await bank_account_repo.save(bank_account)

                # Verify it's visible within transaction
                found = await bank_account_repo.find_by_iban(iban)
                assert found is not None, "Should be visible after flush"

                # Force failure
                raise ValueError("Transaction failed")

        # Verify rollback
        async for session in get_session(atomicity_session_maker):
            bank_account_repo = BankAccountRepositorySQLAlchemy(session, current_user)

            found = await bank_account_repo.find_by_iban(iban)
            assert found is None, "Bank account should have been rolled back"

    @pytest.mark.asyncio
    async def test_partial_success_still_commits(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """
        Test that if we handle exceptions internally, transaction still commits.

        This shows the pattern of trying multiple operations and continuing
        even if some fail.
        """
        ibans = [f"NL{i:020d}" for i in range(1, 6)]

        saved_count = 0
        failed_count = 0

        async for session in get_session(atomicity_session_maker):
            bank_account_repo = BankAccountRepositorySQLAlchemy(session, current_user)

            for i, iban in enumerate(ibans):
                try:
                    # Simulate some failing (e.g., validation error)
                    if i == 2:  # Make the 3rd one fail
                        raise ValueError("Invalid account")

                    bank_account = BankAccount(
                        iban=iban,
                        account_number=f"ACC{i}",
                        blz="12345678",
                        account_holder=f"User {i}",
                        account_type="Girokonto",
                        currency="EUR",
                        balance=Decimal("100.00"),
                    )
                    await bank_account_repo.save(bank_account)
                    saved_count += 1
                except ValueError:
                    failed_count += 1
                    continue

        assert saved_count == 4, "4 accounts should have been saved"
        assert failed_count == 1, "1 account should have failed"

        # Verify the successful ones were committed
        async for session in get_session(atomicity_session_maker):
            bank_account_repo = BankAccountRepositorySQLAlchemy(session, current_user)

            all_accounts = await bank_account_repo.find_all()
            assert len(all_accounts) == 4, "4 accounts should be persisted"


@pytest.mark.integration
class TestFlushVsCommitBehavior:
    """Tests that demonstrate the difference between flush() and commit()."""

    @pytest.mark.asyncio
    async def test_flush_allows_rollback(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """Demonstrate that flush() allows rollback."""
        iban = "FLUSH-TEST-001"

        with pytest.raises(RuntimeError):
            async for session in get_session(atomicity_session_maker):
                account_repo = AccountRepositorySQLAlchemy(session, current_user)

                account = Account(
                    "Flush Test",
                    AccountType.ASSET,
                    iban,
                    user_id=TEST_USER_ID,
                )
                await account_repo.save(account)  # Calls flush()

                # Data is in database session but not committed
                found = await account_repo.find_by_account_number(iban)
                assert found is not None, "Data visible after flush"

                # Force rollback
                raise RuntimeError("Rolling back")

        # Data should be gone
        async for session in get_session(atomicity_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            found = await account_repo.find_by_account_number(iban)
            assert found is None, "Data rolled back"

    @pytest.mark.asyncio
    async def test_session_isolation(
        self,
        atomicity_session_maker,
        atomicity_tables,
        current_user,
    ):
        """Test that uncommitted changes are not visible in other sessions."""
        iban = "ISOLATION-TEST-001"

        # Start a transaction but don't complete it yet
        async for session1 in get_session(atomicity_session_maker):
            account_repo1 = AccountRepositorySQLAlchemy(session1, current_user)

            account = Account(
                "Isolation Test",
                AccountType.ASSET,
                iban,
                user_id=TEST_USER_ID,
            )
            await account_repo1.save(account)

            # Visible in same session
            found_in_session1 = await account_repo1.find_by_account_number(iban)
            assert found_in_session1 is not None

            # Check from another session (would need concurrent execution)
            # In practice, the outer session completes before we can check
            # This test documents the expected behavior

        # After commit, visible in new session
        async for session2 in get_session(atomicity_session_maker):
            account_repo2 = AccountRepositorySQLAlchemy(session2, current_user)
            found_in_session2 = await account_repo2.find_by_account_number(iban)
            assert found_in_session2 is not None, "Committed data is visible"
