"""Tests for CounterAccountResolutionService with AI integration."""

from datetime import date
from decimal import Decimal
from typing import Optional
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.banking.value_objects import BankTransaction
from swen.domain.integration.services import (
    AICounterAccountProvider,
    CounterAccountResolutionService,
)
from swen.domain.integration.value_objects import (
    AICounterAccountResult,
    CounterAccountOption,
)

# Test user ID
TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


# Mock AI Provider for testing
class MockAIProvider(AICounterAccountProvider):
    """Mock AI provider for testing."""

    def __init__(
        self,
        result: Optional[AICounterAccountResult] = None,
        model: str = "mock-model",
        raise_error: bool = False,
    ):
        self._result = result
        self._model = model
        self._raise_error = raise_error
        self.resolve_called = False
        self.last_transaction: Optional[BankTransaction] = None
        self.last_accounts: Optional[list[CounterAccountOption]] = None

    async def resolve(
        self,
        transaction: BankTransaction,
        available_accounts: list[CounterAccountOption],
        user_id: UUID | None = None,
    ) -> Optional[AICounterAccountResult]:
        self.resolve_called = True
        self.last_transaction = transaction
        self.last_accounts = available_accounts
        self.last_user_id = user_id

        if self._raise_error:
            msg = "AI service unavailable"
            raise RuntimeError(msg)

        return self._result

    @property
    def model_name(self) -> str:
        return self._model

    async def health_check(self) -> bool:
        return True

    async def ensure_model_available(self, auto_pull: bool = True) -> bool:
        return True


# Helper functions
def create_bank_transaction(**overrides) -> BankTransaction:
    """Create a test bank transaction."""
    defaults = {
        "booking_date": date(2025, 1, 15),
        "value_date": date(2025, 1, 15),
        "amount": Decimal("-50.00"),
        "currency": "EUR",
        "purpose": "REWE Supermarkt",
        "applicant_name": "REWE Markt GmbH",
    }
    defaults.update(overrides)
    return BankTransaction(**defaults)


def create_account(
    account_type: AccountType,
    account_number: str,
    name: str,
) -> Account:
    """Create a test account."""
    return Account(
        name=name,
        account_type=account_type,
        account_number=account_number,
        user_id=TEST_USER_ID,
        default_currency=Currency("EUR"),
    )


@pytest.fixture
def groceries_account() -> Account:
    """Groceries expense account."""
    return create_account(AccountType.EXPENSE, "4000", "Lebensmittel (Groceries)")


@pytest.fixture
def utilities_account() -> Account:
    """Utilities expense account."""
    return create_account(AccountType.EXPENSE, "4100", "Nebenkosten (Utilities)")


@pytest.fixture
def salary_account() -> Account:
    """Salary income account."""
    return create_account(AccountType.INCOME, "3000", "Gehälter (Salaries)")


@pytest.fixture
def other_expense_account() -> Account:
    """Sonstiges (Other) expense account."""
    return create_account(AccountType.EXPENSE, "4900", "Sonstiges (Other)")


@pytest.fixture
def bank_account() -> Account:
    """Bank asset account."""
    return create_account(AccountType.ASSET, "1000", "Bank Account")


@pytest.fixture
def mock_account_repository(
    groceries_account,
    utilities_account,
    salary_account,
    other_expense_account,
    bank_account,
):
    """Mock account repository with test accounts."""
    accounts = {
        groceries_account.id: groceries_account,
        utilities_account.id: utilities_account,
        salary_account.id: salary_account,
        other_expense_account.id: other_expense_account,
        bank_account.id: bank_account,
    }

    repo = AsyncMock()
    repo.find_by_id.side_effect = lambda id: accounts.get(id)
    repo.find_all.return_value = list(accounts.values())
    return repo


@pytest.fixture
def mock_rule_repository():
    """Mock rule repository with no rules."""
    repo = AsyncMock()
    repo.find_all_active.return_value = []
    return repo


class TestCounterAccountResolutionServiceWithoutAI:
    """Tests for service without AI provider (backward compatibility)."""

    @pytest.mark.asyncio
    async def test_service_without_ai_provider(
        self,
        mock_rule_repository,
        mock_account_repository,
    ):
        """Service should work without AI provider."""
        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
        )

        assert service.has_ai_provider is False

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        # No rules, no AI = None
        assert result is None

    @pytest.mark.asyncio
    async def test_resolve_with_details_without_ai(
        self,
        mock_rule_repository,
        mock_account_repository,
    ):
        """resolve_counter_account_with_details should work without AI."""
        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
        )

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account_with_details(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        assert result.account is None
        assert result.ai_result is None
        assert result.source == "none"


class TestCounterAccountResolutionServiceWithAI:
    """Tests for service with AI provider."""

    @pytest.mark.asyncio
    async def test_service_with_ai_provider(
        self,
        mock_rule_repository,
        mock_account_repository,
        groceries_account,
    ):
        """Service should use AI when no rules match."""
        ai_result = AICounterAccountResult(
            counter_account_id=groceries_account.id,
            confidence=0.9,
            reasoning="REWE is a grocery store",
        )
        ai_provider = MockAIProvider(result=ai_result)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
            ai_provider=ai_provider,
        )

        assert service.has_ai_provider is True

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        assert result is not None
        assert result.id == groceries_account.id
        assert ai_provider.resolve_called is True

    @pytest.mark.asyncio
    async def test_ai_provides_detailed_result(
        self,
        mock_rule_repository,
        mock_account_repository,
        groceries_account,
    ):
        """AI result should include confidence and reasoning."""
        ai_result = AICounterAccountResult(
            counter_account_id=groceries_account.id,
            confidence=0.85,
            reasoning="Transaction from REWE indicates grocery purchase",
        )
        ai_provider = MockAIProvider(result=ai_result)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account_with_details(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        assert result.account is not None
        assert result.source == "ai"
        assert result.ai_result is not None
        assert result.ai_result.confidence == 0.85
        assert (
            result.ai_result.reasoning
            == "Transaction from REWE indicates grocery purchase"
        )

    @pytest.mark.asyncio
    async def test_ai_receives_expense_and_income_accounts_only(
        self,
        mock_rule_repository,
        mock_account_repository,
        groceries_account,
    ):
        """AI should only receive expense and income accounts, not assets."""
        ai_result = AICounterAccountResult(
            counter_account_id=groceries_account.id,
            confidence=0.9,
        )
        ai_provider = MockAIProvider(result=ai_result)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction()
        await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        # Check that AI only received expense/income accounts
        assert ai_provider.last_accounts is not None
        account_types = {acc.account_type for acc in ai_provider.last_accounts}
        assert account_types == {"expense", "income"}
        assert "asset" not in account_types


class TestAIErrorHandling:
    """Tests for AI error handling."""

    @pytest.mark.asyncio
    async def test_ai_error_falls_back_gracefully(
        self,
        mock_rule_repository,
        mock_account_repository,
    ):
        """AI errors should not break the service."""
        ai_provider = MockAIProvider(raise_error=True)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        # Should return None, not raise exception
        assert result is None
        assert ai_provider.resolve_called is True

    @pytest.mark.asyncio
    async def test_ai_returns_none_handled(
        self,
        mock_rule_repository,
        mock_account_repository,
    ):
        """AI returning None should be handled gracefully."""
        ai_provider = MockAIProvider(result=None)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_ai_invalid_account_id_rejected(
        self,
        mock_rule_repository,
        mock_account_repository,
    ):
        """AI suggesting non-existent account should be rejected."""
        invalid_id = uuid4()  # Not in repository
        ai_result = AICounterAccountResult(
            counter_account_id=invalid_id,
            confidence=0.95,
        )
        ai_provider = MockAIProvider(result=ai_result)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        # Invalid account ID should be rejected
        assert result is None


class TestResolutionPriority:
    """Tests for resolution priority (rules > AI)."""

    @pytest.mark.asyncio
    async def test_rules_take_priority_over_ai(
        self,
        mock_account_repository,
        groceries_account,
        utilities_account,
    ):
        """User rules should take priority over AI suggestions."""
        from swen.domain.integration.value_objects import (
            CounterAccountRule,
            PatternType,
            RuleSource,
        )

        # Create a rule that matches
        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=groceries_account.id,
            user_id=TEST_USER_ID,
            priority=100,
            source=RuleSource.USER_CREATED,
        )

        rule_repo = AsyncMock()
        rule_repo.find_all_active.return_value = [rule]
        rule_repo.save = AsyncMock()

        # AI would suggest a different account
        ai_result = AICounterAccountResult(
            counter_account_id=utilities_account.id,
            confidence=0.99,
        )
        ai_provider = MockAIProvider(result=ai_result)

        service = CounterAccountResolutionService(
            rule_repository=rule_repo,
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction(applicant_name="REWE Markt")
        result = await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        # Rule should win over AI
        assert result is not None
        assert result.id == groceries_account.id
        # AI should NOT have been called
        assert ai_provider.resolve_called is False

    @pytest.mark.asyncio
    async def test_ai_used_when_no_rules_match(
        self,
        mock_rule_repository,
        mock_account_repository,
        groceries_account,
    ):
        """AI should be used when no rules match."""
        ai_result = AICounterAccountResult(
            counter_account_id=groceries_account.id,
            confidence=0.9,
        )
        ai_provider = MockAIProvider(result=ai_result)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,  # No rules
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        assert result is not None
        assert result.id == groceries_account.id
        assert ai_provider.resolve_called is True


class TestResolutionResultDetails:
    """Tests for ResolutionResult details."""

    @pytest.mark.asyncio
    async def test_resolution_result_source_rule(
        self,
        mock_account_repository,
        groceries_account,
    ):
        """Resolution from rule should have source='rule'."""
        from swen.domain.integration.value_objects import (
            CounterAccountRule,
            PatternType,
            RuleSource,
        )

        rule = CounterAccountRule(
            pattern_type=PatternType.COUNTERPARTY_NAME,
            pattern_value="REWE",
            counter_account_id=groceries_account.id,
            user_id=TEST_USER_ID,
            priority=100,
            source=RuleSource.USER_CREATED,
        )

        rule_repo = AsyncMock()
        rule_repo.find_all_active.return_value = [rule]
        rule_repo.save = AsyncMock()

        service = CounterAccountResolutionService(rule_repository=rule_repo)

        transaction = create_bank_transaction(applicant_name="REWE Markt")
        result = await service.resolve_counter_account_with_details(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        assert result.source == "rule"
        assert result.ai_result is None

    @pytest.mark.asyncio
    async def test_resolution_result_source_ai(
        self,
        mock_rule_repository,
        mock_account_repository,
        groceries_account,
    ):
        """Resolution from AI should have source='ai' and include AI result."""
        ai_result = AICounterAccountResult(
            counter_account_id=groceries_account.id,
            confidence=0.88,
            reasoning="Grocery store detected",
        )
        ai_provider = MockAIProvider(result=ai_result)

        service = CounterAccountResolutionService(
            rule_repository=mock_rule_repository,
            ai_provider=ai_provider,
        )

        transaction = create_bank_transaction()
        result = await service.resolve_counter_account_with_details(
            bank_transaction=transaction,
            account_repository=mock_account_repository,
        )

        assert result.source == "ai"
        assert result.ai_result is not None
        assert result.ai_result.confidence == 0.88
        assert result.ai_result.reasoning == "Grocery store detected"
