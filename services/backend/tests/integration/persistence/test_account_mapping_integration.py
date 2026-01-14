"""
Integration test for AccountMapping repository with real database session.

This test mimics the exact flow from the bank_account_import_flow.ipynb notebook
to reproduce the bug where the second bank account mapping is not stored.
"""

import os
from typing import AsyncGenerator
from uuid import UUID, uuid4

import pytest
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from swen.application.services import BankAccountImportService
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankAccount
from swen.domain.integration.entities import AccountMapping
from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
)

# Load environment variables
load_dotenv()
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


@pytest.fixture
def database_url():
    """Get database URL from environment or use test database."""
    # Use test database URL if available, otherwise use in-memory SQLite
    return os.getenv(
        "TEST_DATABASE_URL",
        "sqlite+aiosqlite:///:memory:",
    )


@pytest.fixture
async def integration_engine(database_url) -> AsyncGenerator[AsyncEngine, None]:
    """Create a fresh database engine for each test."""
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def integration_session_maker(
    integration_engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    """Create a session maker for integration tests."""
    return async_sessionmaker(
        integration_engine,
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
class TestAccountMappingIntegration:
    """Integration tests for AccountMapping using real database sessions."""

    async def test_save_single_mapping_with_db_manager(
        self,
        integration_session_maker,
        current_user,
    ):
        """Test saving a single mapping using the database manager."""
        test_iban = "DE89370400440532013000"

        # Simulate the notebook pattern: async for session in get_session()
        async for session in get_session(integration_session_maker):
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Create and save mapping
            mapping = AccountMapping(
                iban=test_iban,
                accounting_account_id=uuid4(),
                account_name="Test Account",
                is_active=True,
                user_id=TEST_USER_ID,
            )

            await mapping_repo.save(mapping)

            # Verify within same session
            found = await mapping_repo.find_by_iban(mapping.iban)
            assert found is not None
            assert found.iban == mapping.iban

        # Verify in new session (persisted)
        async for session in get_session(integration_session_maker):
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)
            found = await mapping_repo.find_by_iban(test_iban)
            assert found is not None, "Mapping should persist across sessions"

    async def test_save_two_mappings_with_db_manager(
        self,
        integration_session_maker,
        current_user,
    ):
        """
        Test saving two mappings using database manager.

        This reproduces the notebook flow where two bank accounts
        are imported in sequence.
        """
        mapping1_iban = "NL12TRIO0123456789"
        mapping2_iban = "NL34TRIO0987654321"

        # First session: Save both mappings (like notebook does)
        async for session in get_session(integration_session_maker):
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Create first mapping
            mapping1 = AccountMapping(
                iban=mapping1_iban,
                accounting_account_id=uuid4(),
                account_name="Triodos - Betaalrekening",
                is_active=True,
                user_id=TEST_USER_ID,
            )
            await mapping_repo.save(mapping1)

            # Create second mapping
            mapping2 = AccountMapping(
                iban=mapping2_iban,
                accounting_account_id=uuid4(),
                account_name="Triodos - Spaarrekening",
                is_active=True,
                user_id=TEST_USER_ID,
            )
            await mapping_repo.save(mapping2)

            # Verify within same session
            found1 = await mapping_repo.find_by_iban(mapping1_iban)
            found2 = await mapping_repo.find_by_iban(mapping2_iban)
            assert found1 is not None, "First mapping should exist in session"
            assert found2 is not None, "Second mapping should exist in session"

            all_mappings = await mapping_repo.find_all()
            assert len(all_mappings) >= 2, (
                f"Should have at least 2 mappings, got {len(all_mappings)}"
            )

        # Second session: Verify both persist (like notebook idempotency test)
        async for session in get_session(integration_session_maker):
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Find both mappings
            found1 = await mapping_repo.find_by_iban(mapping1_iban)
            found2 = await mapping_repo.find_by_iban(mapping2_iban)

            assert found1 is not None, (
                "First Triodos mapping should persist across sessions"
            )
            assert found2 is not None, (
                "Second Triodos mapping should persist across sessions - "
                "THIS IS THE BUG!"
            )

            # Verify count
            all_mappings = await mapping_repo.find_all()
            triodos_mappings = [
                m for m in all_mappings if m.iban in [mapping1_iban, mapping2_iban]
            ]
            assert len(triodos_mappings) == 2, (
                f"Expected 2 Triodos mappings, got {len(triodos_mappings)}"
            )

    async def test_import_multiple_bank_accounts_full_flow(
        self,
        integration_session_maker,
        current_user,
    ):
        """
        Test the complete import flow from notebook.

        This is the exact scenario:
        1. Create accounting accounts
        2. Import 2 bank accounts using BankAccountImportService
        3. Verify both mappings persist
        4. Test idempotency
        """
        # Create mock bank accounts (like from FinTS)
        bank_account_1 = BankAccount(
            iban="NL12TRIO0123456789",
            account_number="123456789",
            blz="12345678",  # BLZ needs 8 chars
            account_holder="Test User",
            account_type="Betaalrekening",
            currency="EUR",
            bic="TRIODEFFXXX",
            bank_name="Triodos Bank",
        )

        bank_account_2 = BankAccount(
            iban="NL34TRIO0987654321",
            account_number="987654321",
            blz="12345678",  # BLZ needs 8 chars
            account_holder="Test User",
            account_type="Spaarrekening",
            currency="EUR",
            bic="TRIODEFFXXX",
            bank_name="Triodos Bank",
        )

        # === FIRST IMPORT ===
        async for session in get_session(integration_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            import_service = BankAccountImportService(
                account_repository=account_repo,
                mapping_repository=mapping_repo,
                current_user=current_user,
            )

            # Import both bank accounts
            results = await import_service.import_multiple_bank_accounts(
                [bank_account_1, bank_account_2],
            )

            # Verify results
            assert len(results) == 2, (
                f"Should have imported 2 accounts, got {len(results)}"
            )

            # Verify both mappings exist in session
            mapping1 = await mapping_repo.find_by_iban(bank_account_1.iban)
            mapping2 = await mapping_repo.find_by_iban(bank_account_2.iban)

            assert mapping1 is not None, "First mapping should exist after import"
            assert mapping2 is not None, "Second mapping should exist after import"

        # === VERIFY PERSISTENCE ===
        async for session in get_session(integration_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Check mappings persist
            all_mappings = await mapping_repo.find_all()
            triodos_mappings = [
                m
                for m in all_mappings
                if bank_account_1.iban in m.iban or bank_account_2.iban in m.iban
            ]

            assert len(triodos_mappings) == 2, (
                f"Expected 2 persisted Triodos mappings, got "
                f"{len(triodos_mappings)}: {[m.iban for m in triodos_mappings]}"
            )

            mapping1 = await mapping_repo.find_by_iban(bank_account_1.iban)
            mapping2 = await mapping_repo.find_by_iban(bank_account_2.iban)

            assert mapping1 is not None, (
                "First Triodos mapping should persist - CRITICAL BUG"
            )
            assert mapping2 is not None, (
                "Second Triodos mapping should persist - THIS IS THE BUG!"
            )

        # === TEST IDEMPOTENCY ===
        async for session in get_session(integration_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            import_service = BankAccountImportService(
                account_repository=account_repo,
                mapping_repository=mapping_repo,
                current_user=current_user,
            )

            # Count before
            mappings_before = await mapping_repo.find_all()
            accounts_before = await account_repo.find_all_active()

            # Re-import same accounts
            results = await import_service.import_multiple_bank_accounts(
                [bank_account_1, bank_account_2],
            )

            # Count after
            mappings_after = await mapping_repo.find_all()
            accounts_after = await account_repo.find_all_active()

            # Should be idempotent (no duplicates)
            assert len(mappings_after) == len(mappings_before), (
                f"Mappings should not duplicate: "
                f"before={len(mappings_before)}, after={len(mappings_after)}"
            )
            assert len(accounts_after) == len(accounts_before), (
                f"Accounts should not duplicate: "
                f"before={len(accounts_before)}, after={len(accounts_after)}"
            )

    async def test_sequential_session_pattern(
        self,
        integration_session_maker,
        current_user,
    ):
        """
        Test the pattern of creating multiple items across sequential operations.

        This mimics how the notebook might call save() multiple times
        within a single session context.
        """
        iban1 = "NL11TEST0000000001"
        iban2 = "NL22TEST0000000002"
        iban3 = "NL33TEST0000000003"

        # Single session, multiple saves (like import_multiple_bank_accounts)
        async for session in get_session(integration_session_maker):
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Save 3 mappings sequentially
            for i, iban in enumerate([iban1, iban2, iban3], 1):
                mapping = AccountMapping(
                    iban=iban,
                    accounting_account_id=uuid4(),
                    account_name=f"Test Account {i}",
                    is_active=True,
                    user_id=TEST_USER_ID,
                )
                await mapping_repo.save(mapping)

                # Verify immediately after save
                found = await mapping_repo.find_by_iban(iban)
                assert found is not None, (
                    f"Mapping {i} should be findable immediately after save"
                )

            # Verify all at end of session
            all_mappings = await mapping_repo.find_all()
            test_mappings = [m for m in all_mappings if m.iban in [iban1, iban2, iban3]]
            assert len(test_mappings) == 3, (
                f"Expected 3 test mappings in session, got {len(test_mappings)}"
            )

        # Verify all persist in new session
        async for session in get_session(integration_session_maker):
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            found1 = await mapping_repo.find_by_iban(iban1)
            found2 = await mapping_repo.find_by_iban(iban2)
            found3 = await mapping_repo.find_by_iban(iban3)

            assert found1 is not None, "Mapping 1 should persist"
            assert found2 is not None, "Mapping 2 should persist - BUG CHECK"
            assert found3 is not None, "Mapping 3 should persist - BUG CHECK"

            all_mappings = await mapping_repo.find_all()
            test_mappings = [m for m in all_mappings if m.iban in [iban1, iban2, iban3]]
            assert len(test_mappings) == 3, (
                f"Expected 3 persisted test mappings, got {len(test_mappings)}"
            )

    async def test_account_and_mapping_together(
        self,
        integration_session_maker,
        current_user,
    ):
        """
        Test creating both Account and AccountMapping in same session.

        This is what BankAccountImportService does:
        1. Create Account
        2. Save Account
        3. Create AccountMapping with Account.id
        4. Save AccountMapping
        """
        iban = "DE89370400440532013000"

        async for session in get_session(integration_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Create account (using IBAN as account_number for deterministic UUID)
            account = Account(
                name="DKB - Girokonto",
                account_type=AccountType.ASSET,
                account_number=iban,  # ← Key: IBAN as account_number
                default_currency=Currency("EUR"),
                user_id=TEST_USER_ID,
            )

            # Save account
            await account_repo.save(account)

            # Create mapping with account ID
            mapping = AccountMapping(
                iban=iban,
                accounting_account_id=account.id,  # ← Links to account
                account_name="DKB - Girokonto",
                is_active=True,
                user_id=TEST_USER_ID,
            )

            # Save mapping
            await mapping_repo.save(mapping)

            # Verify both exist in session
            found_account = await account_repo.find_by_id(account.id)
            found_mapping = await mapping_repo.find_by_iban(iban)

            assert found_account is not None
            assert found_mapping is not None
            assert found_mapping.accounting_account_id == account.id

        # Verify both persist
        async for session in get_session(integration_session_maker):
            account_repo = AccountRepositorySQLAlchemy(session, current_user)
            mapping_repo = AccountMappingRepositorySQLAlchemy(session, current_user)

            # Find mapping
            found_mapping = await mapping_repo.find_by_iban(iban)
            assert found_mapping is not None, "Mapping should persist"

            # Find account via mapping
            found_account = await account_repo.find_by_id(
                found_mapping.accounting_account_id,
            )
            assert found_account is not None, "Linked account should persist"
            assert found_account.account_number == iban
