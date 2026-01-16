"""Integration tests for AI counter-account resolution.

These tests verify the AI components work together correctly.
Tests that require a running Ollama instance are marked with @pytest.mark.ollama
and will be skipped if Ollama is not available.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio

from swen.application.commands.accounting import GenerateDefaultAccountsCommand
from swen.application.factories.bank_import_transaction_factory import (
    BankImportTransactionFactory,
)
from swen.application.ports.identity import CurrentUser
from swen.application.queries.integration import OpeningBalanceQuery
from swen.application.services import (
    BankAccountImportService,
    OpeningBalanceAdjustmentService,
    TransactionImportService,
)
from swen.application.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)
from swen.domain.banking.repositories.bank_transaction_repository import (
    StoredBankTransaction,
)
from swen.domain.banking.value_objects import BankAccount, BankTransaction
from swen.domain.integration.services import CounterAccountResolutionService
from swen.domain.integration.value_objects import CounterAccountOption
from swen.infrastructure.integration.ai import OllamaCounterAccountProvider
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    CounterAccountRuleRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)

# Import Testcontainers fixtures
from tests.shared.fixtures.database import (
    TEST_USER_EMAIL,
    TEST_USER_ID,
)

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures for Ollama availability check
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ollama_available():
    """Check if Ollama is running and available."""
    import httpx

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:11434/api/tags")
            return response.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


@pytest.fixture(scope="module")
def ollama_model_available(ollama_available):
    """Check if the required model is available in Ollama."""
    if not ollama_available:
        return False

    import httpx

    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get("http://localhost:11434/api/tags")
            if response.status_code != 200:
                return False

            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]

            # Check for any of the recommended models
            for name in model_names:
                if "qwen2.5" in name or "llama" in name or "mistral" in name:
                    return True
            return False
    except Exception:
        return False


@pytest.fixture
def skip_if_no_ollama(ollama_available):
    """Skip test if Ollama is not available."""
    if not ollama_available:
        pytest.skip("Ollama is not running. Start with: ollama serve")


@pytest.fixture
def skip_if_no_model(ollama_model_available):
    """Skip test if no suitable model is available."""
    if not ollama_model_available:
        pytest.skip(
            "No suitable model available. Pull with: ollama pull qwen2.5:3b",
        )


# ---------------------------------------------------------------------------
# Database fixtures (using Testcontainers PostgreSQL via shared fixtures)
# ---------------------------------------------------------------------------


@pytest.fixture
def current_user() -> CurrentUser:
    """Provide a CurrentUser for the test user."""
    return CurrentUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)


@pytest_asyncio.fixture
async def repositories(db_session, current_user):
    """Wire repositories together and seed standard chart of accounts."""
    account_repo = AccountRepositorySQLAlchemy(db_session, current_user)
    # Use the command instead of the deprecated domain service
    generate_accounts_cmd = GenerateDefaultAccountsCommand(
        account_repository=account_repo,
        current_user=current_user,
    )
    await generate_accounts_cmd.execute()

    yield SimpleNamespace(
        session=db_session,
        account_repo=account_repo,
        transaction_repo=TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        ),
        mapping_repo=AccountMappingRepositorySQLAlchemy(db_session, current_user),
        import_repo=TransactionImportRepositorySQLAlchemy(db_session, current_user),
        rule_repo=CounterAccountRuleRepositorySQLAlchemy(db_session, current_user),
        user_id=TEST_USER_ID,
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# Test transactions
# ---------------------------------------------------------------------------


@pytest.fixture
def grocery_transaction() -> BankTransaction:
    """A transaction that should be classified as groceries."""
    return BankTransaction(
        booking_date=date(2025, 1, 15),
        value_date=date(2025, 1, 15),
        amount=Decimal("-47.83"),
        currency="EUR",
        purpose="REWE SAGT DANKE 12345",
        applicant_name="REWE Markt GmbH",
    )


@pytest.fixture
def streaming_transaction() -> BankTransaction:
    """A transaction that should be classified as streaming/entertainment."""
    return BankTransaction(
        booking_date=date(2025, 1, 16),
        value_date=date(2025, 1, 16),
        amount=Decimal("-15.99"),
        currency="EUR",
        purpose="Netflix Monatsabo",
        applicant_name="NETFLIX.COM",
    )


@pytest.fixture
def transport_transaction() -> BankTransaction:
    """A transaction that should be classified as transport."""
    return BankTransaction(
        booking_date=date(2025, 1, 17),
        value_date=date(2025, 1, 17),
        amount=Decimal("-89.00"),
        currency="EUR",
        purpose="ICE Ticket München - Berlin",
        applicant_name="Deutsche Bahn AG",
    )


@pytest.fixture
def salary_transaction() -> BankTransaction:
    """An income transaction (salary)."""
    return BankTransaction(
        booking_date=date(2025, 1, 25),
        value_date=date(2025, 1, 25),
        amount=Decimal("3500.00"),
        currency="EUR",
        purpose="Gehalt Januar 2025",
        applicant_name="Arbeitgeber GmbH",
    )


# ---------------------------------------------------------------------------
# Integration Tests: AI Provider
# ---------------------------------------------------------------------------


class TestOllamaProviderIntegration:
    """Integration tests for OllamaCounterAccountProvider with real Ollama."""

    @pytest.mark.asyncio
    async def test_provider_health_check(self, skip_if_no_ollama):
        """Provider health check should return True when Ollama is running."""
        provider = OllamaCounterAccountProvider(
            model="qwen2.5:3b",
            min_confidence=0.5,
        )

        is_healthy = await provider.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_provider_resolves_grocery_transaction(
        self,
        skip_if_no_ollama,
        skip_if_no_model,
        grocery_transaction,
    ):
        """Provider should classify grocery transaction correctly."""
        provider = OllamaCounterAccountProvider(
            model="qwen2.5:3b",
            min_confidence=0.5,
        )

        from uuid import uuid4

        groceries_id = uuid4()
        accounts = [
            CounterAccountOption(
                account_id=groceries_id,
                account_number="4000",
                name="Supermarkt & Lebensmittel",
                account_type="expense",
            ),
            CounterAccountOption(
                account_id=uuid4(),
                account_number="4100",
                name="Streaming & Unterhaltung",
                account_type="expense",
            ),
            CounterAccountOption(
                account_id=uuid4(),
                account_number="4900",
                name="Sonstiges",
                account_type="expense",
            ),
        ]

        result = await provider.resolve(grocery_transaction, accounts)

        assert result is not None
        assert result.counter_account_id == groceries_id
        assert result.confidence >= 0.7
        assert result.reasoning is not None

    @pytest.mark.asyncio
    async def test_provider_resolves_streaming_transaction(
        self,
        skip_if_no_ollama,
        skip_if_no_model,
        streaming_transaction,
    ):
        """Provider should classify streaming transaction correctly."""
        provider = OllamaCounterAccountProvider(
            model="qwen2.5:3b",
            min_confidence=0.5,
        )

        from uuid import uuid4

        streaming_id = uuid4()
        accounts = [
            CounterAccountOption(
                account_id=uuid4(),
                account_number="4000",
                name="Supermarkt & Lebensmittel",
                account_type="expense",
            ),
            CounterAccountOption(
                account_id=streaming_id,
                account_number="4100",
                name="Streaming & Unterhaltung",
                account_type="expense",
            ),
            CounterAccountOption(
                account_id=uuid4(),
                account_number="4900",
                name="Sonstiges",
                account_type="expense",
            ),
        ]

        result = await provider.resolve(streaming_transaction, accounts)

        assert result is not None
        assert result.counter_account_id == streaming_id
        assert result.confidence >= 0.7


# ---------------------------------------------------------------------------
# Integration Tests: Resolution Service with AI
# ---------------------------------------------------------------------------


class TestCounterAccountResolutionWithAI:
    """Integration tests for CounterAccountResolutionService with AI."""

    @pytest.mark.asyncio
    async def test_resolution_service_uses_ai_when_no_rules(
        self,
        skip_if_no_ollama,
        skip_if_no_model,
        repositories,
        grocery_transaction,
    ):
        """Resolution service should use AI when no rules match."""
        ai_provider = OllamaCounterAccountProvider(
            model="qwen2.5:3b",
            min_confidence=0.5,
        )

        service = CounterAccountResolutionService(
            rule_repository=repositories.rule_repo,
            ai_provider=ai_provider,
        )

        # No rules defined, so AI should be used
        result = await service.resolve_counter_account_with_details(
            bank_transaction=grocery_transaction,
            account_repository=repositories.account_repo,
        )

        assert result.is_resolved
        assert result.is_from_ai
        assert result.ai_result is not None
        assert result.ai_result.confidence >= 0.5

    @pytest.mark.asyncio
    async def test_resolution_service_stores_ai_reasoning(
        self,
        skip_if_no_ollama,
        skip_if_no_model,
        repositories,
        streaming_transaction,
    ):
        """AI resolution should include reasoning in the result."""
        ai_provider = OllamaCounterAccountProvider(
            model="qwen2.5:3b",
            min_confidence=0.5,
        )

        service = CounterAccountResolutionService(
            rule_repository=repositories.rule_repo,
            ai_provider=ai_provider,
        )

        result = await service.resolve_counter_account_with_details(
            bank_transaction=streaming_transaction,
            account_repository=repositories.account_repo,
        )

        assert result.ai_result is not None
        assert result.ai_result.reasoning is not None
        assert len(result.ai_result.reasoning) > 0


# ---------------------------------------------------------------------------
# Integration Tests: Full Import Flow with AI
# ---------------------------------------------------------------------------


class TestTransactionImportWithAIIntegration:
    """Integration tests for full transaction import with AI."""

    TEST_IBAN = "DE89370400440532013000"

    @pytest_asyncio.fixture
    async def bank_account_service(self, repositories):
        """Bank account import service."""
        return BankAccountImportService(
            account_repository=repositories.account_repo,
            mapping_repository=repositories.mapping_repo,
            current_user=repositories.current_user,
        )

    @pytest_asyncio.fixture
    async def setup_bank_account(self, repositories, bank_account_service):
        """Set up bank account mapping before import tests."""
        # Create a mock bank account
        bank_account = BankAccount(
            iban=self.TEST_IBAN,
            account_number="0532013000",
            blz="37040044",
            bank_name="Test Bank",
            account_holder="Test User",
            account_type="Girokonto",
            currency="EUR",
        )

        # Import the bank account (creates asset account + mapping)
        asset_account, mapping = await bank_account_service.import_bank_account(
            bank_account=bank_account,
        )

        return asset_account, mapping

    @pytest_asyncio.fixture
    async def import_service_with_ai(
        self, repositories, bank_account_service, setup_bank_account
    ):
        """Transaction import service with AI enabled."""
        ai_provider = OllamaCounterAccountProvider(
            model="qwen2.5:3b",
            min_confidence=0.5,
        )

        resolution_service = CounterAccountResolutionService(
            rule_repository=repositories.rule_repo,
            ai_provider=ai_provider,
        )

        ob_query = OpeningBalanceQuery(
            transaction_repository=repositories.transaction_repo,
        )

        transfer_reconciliation_service = TransferReconciliationService(
            transaction_repository=repositories.transaction_repo,
            mapping_repository=repositories.mapping_repo,
            account_repository=repositories.account_repo,
            opening_balance_query=ob_query,
        )

        transaction_factory = BankImportTransactionFactory(
            current_user=repositories.current_user,
            ai_provider=ai_provider,
        )

        ob_adjustment_service = OpeningBalanceAdjustmentService(
            account_repository=repositories.account_repo,
            transaction_repository=repositories.transaction_repo,
            opening_balance_query=ob_query,
            current_user=repositories.current_user,
        )

        return TransactionImportService(
            bank_account_import_service=bank_account_service,
            counter_account_resolution_service=resolution_service,
            transfer_reconciliation_service=transfer_reconciliation_service,
            opening_balance_adjustment_service=ob_adjustment_service,
            transaction_factory=transaction_factory,
            account_repository=repositories.account_repo,
            transaction_repository=repositories.transaction_repo,
            import_repository=repositories.import_repo,
            current_user=repositories.current_user,
        )

    @pytest.mark.asyncio
    async def test_import_stores_ai_metadata(
        self,
        skip_if_no_ollama,
        skip_if_no_model,
        repositories,
        import_service_with_ai,
        grocery_transaction,
    ):
        """Full import flow should store AI metadata in transaction."""
        # Create a stored bank transaction
        stored_tx = StoredBankTransaction(
            id=uuid4(),
            identity_hash="hash_grocery_1",
            hash_sequence=0,
            transaction=grocery_transaction,
            is_imported=False,
            is_new=True,
        )

        results = await import_service_with_ai.import_from_stored_transactions(
            stored_transactions=[stored_tx],
            source_iban=self.TEST_IBAN,
        )

        assert len(results) == 1
        result = results[0]
        assert result.is_success, f"Import failed: {result.error_message}"
        assert result.accounting_transaction is not None

        # Check AI metadata was stored
        ai_metadata = result.accounting_transaction.get_metadata_raw("ai_resolution")
        assert ai_metadata is not None
        assert "confidence" in ai_metadata
        assert "reasoning" in ai_metadata
        assert "model" in ai_metadata
        assert ai_metadata["model"] == "qwen2.5:3b"

    @pytest.mark.asyncio
    async def test_import_multiple_transactions_classifies_correctly(
        self,
        skip_if_no_ollama,
        skip_if_no_model,
        repositories,
        import_service_with_ai,
        grocery_transaction,
        streaming_transaction,
        transport_transaction,
    ):
        """Multiple transactions should be classified to appropriate accounts."""
        transactions = [
            grocery_transaction,
            streaming_transaction,
            transport_transaction,
        ]

        # Create stored bank transactions with unique IDs
        stored_transactions = [
            StoredBankTransaction(
                id=uuid4(),
                identity_hash=f"hash_tx_{i}",
                hash_sequence=0,
                transaction=tx,
                is_imported=False,
                is_new=True,
            )
            for i, tx in enumerate(transactions)
        ]

        results = await import_service_with_ai.import_from_stored_transactions(
            stored_transactions=stored_transactions,
            source_iban=self.TEST_IBAN,
        )

        # All should succeed
        for i, r in enumerate(results):
            assert r.is_success, f"Transaction {i} failed: {r.error_message}"

        # All should have AI metadata
        for result in results:
            ai_metadata = result.accounting_transaction.get_metadata_raw(
                "ai_resolution"
            )
            assert ai_metadata is not None
            assert ai_metadata["confidence"] >= 0.5

        # Transactions should be classified to different accounts
        account_ids = set()
        for result in results:
            ai_metadata = result.accounting_transaction.get_metadata_raw(
                "ai_resolution"
            )
            account_ids.add(ai_metadata["suggested_counter_account_id"])

        # With good classification, at least 2 different accounts
        assert len(account_ids) >= 2, (
            "Expected transactions to be classified differently"
        )
