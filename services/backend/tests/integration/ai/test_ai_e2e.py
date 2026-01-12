"""End-to-end tests for AI counter-account resolution.

These tests verify the complete flow from configuration to transaction
classification. Tests require a running Ollama instance with a model.

Run with: RUN_AI_E2E_TESTS=1 pytest tests/integration/ai/test_ai_e2e.py -v
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from swen.application.context import UserContext
from swen.application.factories import BankImportTransactionFactory
from swen.application.commands.accounting import GenerateDefaultAccountsCommand
from swen.application.services import (
    BankAccountImportService,
    TransactionImportService,
    TransferReconciliationService,
)
from swen.domain.banking.value_objects import BankAccount, BankTransaction
from swen.domain.integration.services import CounterAccountResolutionService
from swen.domain.integration.value_objects import CounterAccountOption
from swen.infrastructure.integration.ai import OllamaCounterAccountProvider
from swen.infrastructure.persistence.sqlalchemy.models.base import Base
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.factory import (
    create_ai_provider_from_settings,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    CounterAccountRuleRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)
from swen_config.settings import get_settings

# Test user
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_USER_EMAIL = "test@example.com"

# Mark all tests in this module
pytestmark = [pytest.mark.integration, pytest.mark.e2e]


# ---------------------------------------------------------------------------
# Skip conditions
# ---------------------------------------------------------------------------


def e2e_enabled() -> bool:
    """Check if E2E tests are enabled via environment variable."""
    return os.getenv("RUN_AI_E2E_TESTS", "").lower() in ("1", "true", "yes")


def ollama_running() -> bool:
    """Check if Ollama is running."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:11434/api/tags")
            return response.status_code == 200
    except Exception:
        return False


def get_available_model() -> str | None:
    """Get the first available suitable model from Ollama."""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:11434/api/tags")
            if response.status_code != 200:
                return None

            models = response.json().get("models", [])
            preferred = ["qwen2.5:3b", "qwen2.5:1.5b", "llama3.2:3b", "mistral:latest"]

            # Check for preferred models first
            for pref in preferred:
                for m in models:
                    if m.get("name", "").startswith(pref.split(":")[0]):
                        return m.get("name")

            # Return any model
            if models:
                return models[0].get("name")
            return None
    except Exception:
        return None


@pytest.fixture(scope="module")
def skip_if_not_enabled():
    """Skip if E2E tests are not explicitly enabled."""
    if not e2e_enabled():
        pytest.skip(
            "AI E2E tests disabled. Set RUN_AI_E2E_TESTS=1 to enable.",
        )


@pytest.fixture(scope="module")
def available_model(skip_if_not_enabled):  # noqa: ARG001
    """Get available model or skip test."""
    if not ollama_running():
        pytest.skip("Ollama is not running. Start with: ollama serve")

    model = get_available_model()
    if not model:
        pytest.skip("No AI models available. Pull with: ollama pull qwen2.5:3b")

    return model


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def e2e_engine():
    """Create an in-memory SQLite engine for E2E tests."""
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False, future=True)


@pytest_asyncio.fixture(scope="function")
async def db_session(e2e_engine):
    """Provide a fresh database with all tables for each test."""
    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        e2e_engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    async with e2e_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def user_context() -> UserContext:
    """Provide a UserContext for the test user."""
    return UserContext(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


TEST_IBAN = "DE89370400440532013000"
TEST_IBAN_2 = "DE89370400440532013001"


@pytest_asyncio.fixture
async def full_setup(db_session, user_context, available_model):
    """Complete setup with all services and AI provider."""
    # Create repositories
    account_repo = AccountRepositorySQLAlchemy(db_session, user_context)
    transaction_repo = TransactionRepositorySQLAlchemy(
        db_session,
        account_repo,
        user_context,
    )
    mapping_repo = AccountMappingRepositorySQLAlchemy(db_session, user_context)
    import_repo = TransactionImportRepositorySQLAlchemy(db_session, user_context)
    rule_repo = CounterAccountRuleRepositorySQLAlchemy(db_session, user_context)

    # Create standard chart of accounts using command (not deprecated service)
    generate_accounts_cmd = GenerateDefaultAccountsCommand(
        account_repository=account_repo,
        user_context=user_context,
    )
    await generate_accounts_cmd.execute()

    # Create AI provider
    ai_provider = OllamaCounterAccountProvider(
        model=available_model,
        min_confidence=0.5,
        timeout=60.0,  # Longer timeout for E2E
    )

    # Create services
    bank_account_service = BankAccountImportService(
        account_repository=account_repo,
        mapping_repository=mapping_repo,
        user_context=user_context,
    )

    # Set up bank account mapping for test IBAN
    bank_account = BankAccount(
        iban=TEST_IBAN,
        account_number="0532013000",
        blz="37040044",
        bank_name="Test Bank",
        account_holder="Test User",
        account_type="Girokonto",
        currency="EUR",
    )
    await bank_account_service.import_bank_account(bank_account=bank_account)

    # Set up second bank account for tests that need different IBANs
    bank_account_2 = BankAccount(
        iban=TEST_IBAN_2,
        account_number="0532013001",
        blz="37040044",
        bank_name="Test Bank",
        account_holder="Test User",
        account_type="Girokonto",
        currency="EUR",
    )
    await bank_account_service.import_bank_account(bank_account=bank_account_2)

    resolution_service = CounterAccountResolutionService(
        rule_repository=rule_repo,
        ai_provider=ai_provider,
    )

    transfer_reconciliation_service = TransferReconciliationService(
        transaction_repository=transaction_repo,
        mapping_repository=mapping_repo,
        account_repository=account_repo,
    )

    transaction_factory = BankImportTransactionFactory(
        user_context=user_context,
        ai_provider=ai_provider,
    )

    import_service = TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=resolution_service,
        transfer_reconciliation_service=transfer_reconciliation_service,
        transaction_factory=transaction_factory,
        account_repository=account_repo,
        transaction_repository=transaction_repo,
        import_repository=import_repo,
        user_context=user_context,
    )

    yield SimpleNamespace(
        account_repo=account_repo,
        transaction_repo=transaction_repo,
        mapping_repo=mapping_repo,
        import_repo=import_repo,
        rule_repo=rule_repo,
        ai_provider=ai_provider,
        bank_account_service=bank_account_service,
        resolution_service=resolution_service,
        import_service=import_service,
        model=available_model,
        test_iban=TEST_IBAN,
        test_iban_2=TEST_IBAN_2,
    )


# ---------------------------------------------------------------------------
# Test data - realistic German transactions
# ---------------------------------------------------------------------------


REALISTIC_TRANSACTIONS = [
    # Groceries
    BankTransaction(
        booking_date=date(2025, 1, 15),
        value_date=date(2025, 1, 15),
        amount=Decimal("-47.83"),
        currency="EUR",
        purpose="REWE SAGT DANKE 54321//BERLIN/DE",
        applicant_name="REWE Markt GmbH",
    ),
    BankTransaction(
        booking_date=date(2025, 1, 16),
        value_date=date(2025, 1, 16),
        amount=Decimal("-32.15"),
        currency="EUR",
        purpose="EDEKA SAGT DANKE 12345",
        applicant_name="EDEKA Minden-Hannover",
    ),
    # Streaming
    BankTransaction(
        booking_date=date(2025, 1, 1),
        value_date=date(2025, 1, 1),
        amount=Decimal("-15.99"),
        currency="EUR",
        purpose="Netflix Monthly Subscription",
        applicant_name="NETFLIX.COM",
    ),
    BankTransaction(
        booking_date=date(2025, 1, 1),
        value_date=date(2025, 1, 1),
        amount=Decimal("-9.99"),
        currency="EUR",
        purpose="Spotify Premium",
        applicant_name="SPOTIFY AB",
    ),
    # Transport
    BankTransaction(
        booking_date=date(2025, 1, 10),
        value_date=date(2025, 1, 10),
        amount=Decimal("-89.00"),
        currency="EUR",
        purpose="Fahrkarte Berlin - München ICE",
        applicant_name="Deutsche Bahn AG",
    ),
    # Restaurant
    BankTransaction(
        booking_date=date(2025, 1, 12),
        value_date=date(2025, 1, 12),
        amount=Decimal("-28.50"),
        currency="EUR",
        purpose="Pizza Bestellung 42",
        applicant_name="LIEFERANDO",
    ),
    # Utilities
    BankTransaction(
        booking_date=date(2025, 1, 5),
        value_date=date(2025, 1, 5),
        amount=Decimal("-85.00"),
        currency="EUR",
        purpose="Stromabschlag Januar 2025",
        applicant_name="Vattenfall Europe Sales GmbH",
    ),
    # Insurance
    BankTransaction(
        booking_date=date(2025, 1, 1),
        value_date=date(2025, 1, 1),
        amount=Decimal("-45.00"),
        currency="EUR",
        purpose="Haftpflichtversicherung",
        applicant_name="Allianz Versicherungs-AG",
    ),
]


# ---------------------------------------------------------------------------
# E2E Tests
# ---------------------------------------------------------------------------


class TestAIE2EFlow:
    """End-to-end tests for the complete AI classification flow."""

    @pytest.mark.asyncio
    async def test_e2e_ai_provider_is_healthy(self, full_setup):
        """AI provider should be healthy and ready."""
        is_healthy = await full_setup.ai_provider.health_check()

        assert is_healthy is True
        print(f"\nAI Provider healthy (model: {full_setup.model})")

    @pytest.mark.asyncio
    async def test_e2e_single_transaction_classification(self, full_setup):
        """Single transaction should be classified and imported successfully."""
        transaction = REALISTIC_TRANSACTIONS[0]  # REWE grocery

        result = await full_setup.import_service.import_transaction(
            bank_transaction=transaction,
            source_iban=full_setup.test_iban,
        )

        assert result.is_success
        assert result.accounting_transaction is not None

        # Should have AI metadata
        ai_metadata = result.accounting_transaction.get_metadata_raw("ai_resolution")
        assert ai_metadata is not None
        assert ai_metadata["confidence"] >= 0.5
        assert ai_metadata["model"] == full_setup.model

        print("\nTransaction classified:")
        account_name = ai_metadata.get("suggested_counter_account_name", "Unknown")
        print(f"   Account: {account_name}")
        print(f"   Confidence: {ai_metadata['confidence']:.0%}")
        print(f"   Reasoning: {ai_metadata.get('reasoning', 'N/A')[:80]}...")

    @pytest.mark.asyncio
    async def test_e2e_batch_transaction_classification(self, full_setup):
        """Multiple transactions should be classified correctly."""
        results = []

        for tx in REALISTIC_TRANSACTIONS:
            result = await full_setup.import_service.import_transaction(
                bank_transaction=tx,
                source_iban=full_setup.test_iban,
            )
            results.append((tx, result))

        # Print classification summary
        print("\nClassification Results:")
        print("-" * 70)

        successful = 0
        high_confidence = 0
        account_distribution: dict[str, int] = {}

        for tx, result in results:
            if result.is_success:
                successful += 1
                ai_metadata = result.accounting_transaction.get_metadata_raw(
                    "ai_resolution",
                )

                if ai_metadata:
                    confidence = ai_metadata.get("confidence", 0)
                    account_name = ai_metadata.get(
                        "suggested_counter_account_name",
                        "Unknown",
                    )

                    if confidence >= 0.7:
                        high_confidence += 1

                    account_distribution[account_name] = (
                        account_distribution.get(account_name, 0) + 1
                    )

                    status = "✓" if confidence >= 0.7 else "?"
                    print(
                        f"{status} {tx.applicant_name[:20]:20} → "
                        f"{account_name[:25]:25} ({confidence:.0%})",
                    )
                else:
                    print(f"{tx.applicant_name[:20]:20} → No AI metadata")
            else:
                print(f"{tx.applicant_name[:20]:20} → Import failed")

        print("-" * 70)
        print(f"Total: {successful}/{len(results)} successful")
        print(f"High confidence (≥70%): {high_confidence}/{successful}")
        print("\nAccount distribution:")
        for account, count in sorted(
            account_distribution.items(),
            key=lambda x: -x[1],
        ):
            print(f"  {account}: {count}")

        # Assertions
        assert successful == len(results), "All transactions should import successfully"
        assert high_confidence >= len(results) * 0.6, (
            "At least 60% should be high confidence"
        )

        # Should use multiple different accounts
        unique_accounts = len(account_distribution)
        assert unique_accounts >= 3, (
            f"Expected at least 3 different accounts, got {unique_accounts}"
        )

    @pytest.mark.asyncio
    async def test_e2e_classification_consistency(self, full_setup):
        """Same transaction type should be classified consistently."""
        # Create two similar grocery transactions
        tx1 = BankTransaction(
            booking_date=date(2025, 1, 15),
            value_date=date(2025, 1, 15),
            amount=Decimal("-25.00"),
            currency="EUR",
            purpose="REWE MARKT 123",
            applicant_name="REWE Markt GmbH",
        )
        tx2 = BankTransaction(
            booking_date=date(2025, 1, 16),
            value_date=date(2025, 1, 16),
            amount=Decimal("-35.00"),
            currency="EUR",
            purpose="REWE MARKT 456",
            applicant_name="REWE Markt GmbH",
        )

        result1 = await full_setup.import_service.import_transaction(
            bank_transaction=tx1,
            source_iban=full_setup.test_iban,
        )
        result2 = await full_setup.import_service.import_transaction(
            bank_transaction=tx2,
            source_iban=full_setup.test_iban_2,  # Different IBAN to avoid duplicate
        )

        assert result1.is_success
        assert result2.is_success

        ai_meta1 = result1.accounting_transaction.get_metadata_raw("ai_resolution")
        ai_meta2 = result2.accounting_transaction.get_metadata_raw("ai_resolution")

        # Both should be classified to the same account
        assert ai_meta1 is not None
        assert ai_meta2 is not None
        assert (
            ai_meta1["suggested_counter_account_id"]
            == ai_meta2["suggested_counter_account_id"]
        ), "Similar transactions should be classified to the same account"

        print("\nConsistency test passed:")
        print(
            f"   Both REWE transactions → {ai_meta1['suggested_counter_account_name']}",
        )

    @pytest.mark.asyncio
    async def test_e2e_income_vs_expense_classification(self, full_setup):
        """Income and expense transactions should use appropriate account types."""
        expense_tx = BankTransaction(
            booking_date=date(2025, 1, 15),
            value_date=date(2025, 1, 15),
            amount=Decimal("-100.00"),
            currency="EUR",
            purpose="Amazon Bestellung",
            applicant_name="AMAZON EU S.A R.L.",
        )

        income_tx = BankTransaction(
            booking_date=date(2025, 1, 25),
            value_date=date(2025, 1, 25),
            amount=Decimal("3500.00"),
            currency="EUR",
            purpose="Gehalt Januar 2025",
            applicant_name="Arbeitgeber GmbH",
        )

        expense_result = await full_setup.import_service.import_transaction(
            bank_transaction=expense_tx,
            source_iban=full_setup.test_iban,
        )
        income_result = await full_setup.import_service.import_transaction(
            bank_transaction=income_tx,
            source_iban=full_setup.test_iban_2,
        )

        assert expense_result.is_success
        assert income_result.is_success

        expense_meta = expense_result.accounting_transaction.get_metadata_raw(
            "ai_resolution",
        )
        income_meta = income_result.accounting_transaction.get_metadata_raw(
            "ai_resolution",
        )

        print("\nIncome/Expense classification:")
        if expense_meta:
            print(f"   Expense → {expense_meta['suggested_counter_account_name']}")
        if income_meta:
            print(f"   Income → {income_meta['suggested_counter_account_name']}")

        # Both should have AI metadata
        assert expense_meta is not None
        assert income_meta is not None

        # They should be classified to different accounts
        assert (
            expense_meta["suggested_counter_account_id"]
            != income_meta["suggested_counter_account_id"]
        )


class TestAIConfigurationE2E:
    """E2E tests for AI configuration and factory integration."""

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("skip_if_not_enabled", "available_model")
    async def test_e2e_factory_creates_ai_provider(self):
        """Factory helper should create AI provider from settings."""
        settings = get_settings()

        # This should work if AI is enabled in config
        if settings.ai_enabled:
            provider = create_ai_provider_from_settings()
            assert provider is not None
            assert isinstance(provider, OllamaCounterAccountProvider)
            print(f"\nFactory created AI provider: {provider.model_name}")
        else:
            print("\nWARNING: AI not enabled in config, skipping factory test")

    @pytest.mark.asyncio
    @pytest.mark.usefixtures("skip_if_not_enabled")
    async def test_e2e_provider_handles_timeout_gracefully(self, available_model):
        """Provider should handle slow responses gracefully."""
        # Create provider with very short timeout
        provider = OllamaCounterAccountProvider(
            model=available_model,
            min_confidence=0.5,
            timeout=0.001,  # 1ms - will definitely timeout
        )

        transaction = BankTransaction(
            booking_date=date(2025, 1, 15),
            value_date=date(2025, 1, 15),
            amount=Decimal("-50.00"),
            currency="EUR",
            purpose="Test transaction",
            applicant_name="Test",
        )

        accounts = [
            CounterAccountOption(
                account_id=uuid4(),
                account_number="4900",
                name="Sonstiges",
                account_type="expense",
            ),
        ]

        # Should return None on timeout, not raise
        result = await provider.resolve(transaction, accounts)

        assert result is None
        print("\nTimeout handled gracefully (returned None)")
