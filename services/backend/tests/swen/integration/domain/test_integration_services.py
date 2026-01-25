"""Integration tests for integration domain services using real FinTS data."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from swen.application.commands.accounting import GenerateDefaultAccountsCommand
from swen.application.factories import BankImportTransactionFactory
from swen.application.queries.integration import OpeningBalanceQuery
from swen.application.services import (
    BankAccountImportService,
    OpeningBalanceAdjustmentService,
    TransactionImportService,
    TransferReconciliationService,
)
from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.integration.services import CounterAccountResolutionService
from swen.domain.integration.value_objects import (
    CounterAccountRule,
    PatternType,
    RuleSource,
)
from swen.domain.shared.time import today_utc
from swen.infrastructure.banking.geldstrom_adapter import GeldstromAdapter
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    CounterAccountRuleRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)

# Load .env from repository root so we share credentials with other integration tests
ROOT_DIR = Path(__file__).parent.parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Skip this module unless integration tests explicitly enabled
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Environment + FinTS fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def integration_enabled():
    """Skip entire module unless RUN_INTEGRATION_TESTS flag enabled."""

    enabled = os.getenv("RUN_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes")
    if not enabled:
        pytest.skip(
            "Integration tests disabled. "
            "Set RUN_INTEGRATION_TESTS=1 in .env to enable.",
        )


@pytest.fixture(scope="module")
def credentials(integration_enabled):  # noqa: ARG001
    """Load FinTS credentials from .env and validate mandatory fields."""

    blz = os.getenv("FINTS_BLZ")
    username = os.getenv("FINTS_USERNAME")
    pin = os.getenv("FINTS_PIN")
    endpoint = os.getenv("FINTS_ENDPOINT")

    missing = [
        name
        for name, value in (
            ("FINTS_BLZ", blz),
            ("FINTS_USERNAME", username),
            ("FINTS_PIN", pin),
            ("FINTS_ENDPOINT", endpoint),
        )
        if not value
    ]
    if missing:
        pytest.skip(
            f"Missing credentials in .env: {', '.join(missing)}. "
            "Copy .env.example to .env and fill in real bank credentials.",
        )

    assert blz is not None
    assert username is not None
    assert pin is not None
    assert endpoint is not None

    if not blz.isdigit() or len(blz) != 8:
        pytest.skip(f"Invalid FINTS_BLZ format: {blz}. Must be 8 digits.")

    return BankCredentials.from_plain(
        blz=blz,
        username=username,
        pin=pin,
        endpoint=endpoint,
    )


@pytest.fixture(scope="module")
def tan_settings():
    """Load TAN settings from environment variables."""
    tan_method = os.getenv("FINTS_TAN_METHOD")
    tan_medium = os.getenv("FINTS_TAN_MEDIUM")

    if not tan_method or not tan_medium:
        pytest.skip(
            "Missing TAN settings in .env: FINTS_TAN_METHOD, FINTS_TAN_MEDIUM. "
            "These are required by some banks to signal TAN capability.",
        )

    return {"tan_method": tan_method, "tan_medium": tan_medium}


@pytest.fixture(scope="module")
async def connected_adapter(credentials, tan_settings):
    """Provide a connected Geldstrom adapter for fetching real data."""

    adapter = GeldstromAdapter()
    adapter.set_tan_method(tan_settings["tan_method"])
    adapter.set_tan_medium(tan_settings["tan_medium"])

    try:
        connected = await adapter.connect(credentials)
        if not connected:
            pytest.fail("Failed to connect to bank with provided credentials")
        yield adapter
    finally:
        if adapter.is_connected():
            await adapter.disconnect()


@pytest.fixture(scope="module")
async def sample_account(connected_adapter):
    """Pick the first available bank account for integration scenarios."""

    accounts = await connected_adapter.fetch_accounts()
    if not accounts:
        pytest.skip("FinTS connection returned no accounts to test with")
    return accounts[0]


@pytest.fixture(scope="module")
async def sample_transactions(connected_adapter, sample_account):
    """Fetch recent transactions for the selected account (30-day window)."""

    start_date = today_utc() - timedelta(days=30)
    transactions = await connected_adapter.fetch_transactions(
        sample_account.iban,
        start_date=start_date,
    )
    if not transactions:
        pytest.skip("No recent transactions available for integration tests")
    return transactions


# ---------------------------------------------------------------------------
# Database + repository fixtures (using Testcontainers PostgreSQL)
# ---------------------------------------------------------------------------

# Import shared Testcontainers fixtures
from tests.shared.fixtures.database import (
    TEST_USER_ID,
)


@pytest_asyncio.fixture()
async def integration_repositories(db_session, current_user):
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


@pytest.fixture
def bank_account_service(integration_repositories):
    """Domain service for mapping FinTS accounts to asset accounts."""

    return BankAccountImportService(
        account_repository=integration_repositories.account_repo,
        mapping_repository=integration_repositories.mapping_repo,
        current_user=integration_repositories.current_user,
    )


@pytest.fixture
def counter_account_resolution_service(integration_repositories):
    """Rule-based counter-account resolution service using SQLAlchemy repository."""

    return CounterAccountResolutionService(
        rule_repository=integration_repositories.rule_repo,
    )


@pytest.fixture
def transaction_import_service(
    integration_repositories,
    bank_account_service,
    counter_account_resolution_service,
):
    """Full transaction import orchestration service."""
    ob_query = OpeningBalanceQuery(
        transaction_repository=integration_repositories.transaction_repo,
    )

    transfer_reconciliation_service = TransferReconciliationService(
        transaction_repository=integration_repositories.transaction_repo,
        mapping_repository=integration_repositories.mapping_repo,
        account_repository=integration_repositories.account_repo,
        opening_balance_query=ob_query,
    )

    transaction_factory = BankImportTransactionFactory(
        current_user=integration_repositories.current_user,
    )

    ob_adjustment_service = OpeningBalanceAdjustmentService(
        account_repository=integration_repositories.account_repo,
        transaction_repository=integration_repositories.transaction_repo,
        opening_balance_query=ob_query,
        current_user=integration_repositories.current_user,
    )

    return TransactionImportService(
        bank_account_import_service=bank_account_service,
        counter_account_resolution_service=counter_account_resolution_service,
        transfer_reconciliation_service=transfer_reconciliation_service,
        opening_balance_adjustment_service=ob_adjustment_service,
        transaction_factory=transaction_factory,
        account_repository=integration_repositories.account_repo,
        transaction_repository=integration_repositories.transaction_repo,
        import_repository=integration_repositories.import_repo,
        current_user=integration_repositories.current_user,
    )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _extract_keyword_from_transaction_purpose(purpose: str | None) -> str:
    """Return a short keyword from a transaction purpose for rule creation."""

    if not purpose:
        return ""
    return purpose.strip().split()[0][:20]


# ---------------------------------------------------------------------------
# Integration tests for domain services
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bank_account_import_service_creates_asset_account(
    integration_repositories,
    bank_account_service,
    sample_account,
):
    """Ensure FinTS accounts become accounting assets with reusable mappings."""

    user_id = integration_repositories.user_id
    asset_account, mapping = await bank_account_service.import_bank_account(
        sample_account,
    )

    assert asset_account.account_number == sample_account.iban
    assert mapping.iban == sample_account.iban

    stored_mapping = await integration_repositories.mapping_repo.find_by_iban(
        sample_account.iban,
    )
    assert stored_mapping is not None

    # Service must be idempotent for repeated imports
    second_account, second_mapping = await bank_account_service.import_bank_account(
        sample_account,
    )
    assert second_account.id == asset_account.id
    assert second_mapping.id == mapping.id


@pytest.mark.asyncio
async def test_counter_account_resolution_service_matches_saved_rule(
    integration_repositories,
    counter_account_resolution_service,
    sample_transactions,
):
    """Counter-account rules from the repository should drive account suggestions."""

    transaction = next(
        (
            tx
            for tx in sample_transactions
            if _extract_keyword_from_transaction_purpose(tx.purpose)
        ),
        None,
    )
    if not transaction:
        pytest.skip(
            "Need at least one transaction with a purpose for counter-account resolution test",
        )

    candidate_keyword = _extract_keyword_from_transaction_purpose(transaction.purpose)
    if not candidate_keyword:
        pytest.skip("Unable to derive keyword for counter-account rule")

    account_repo = integration_repositories.account_repo
    groceries_account = await account_repo.find_by_account_number("4000")
    if not groceries_account:
        pytest.skip("Standard groceries account (4000) missing from chart of accounts")

    rule = CounterAccountRule(
        pattern_type=PatternType.PURPOSE_TEXT,
        pattern_value=candidate_keyword,
        counter_account_id=groceries_account.id,
        priority=200,
        source=RuleSource.USER_CREATED,
        user_id=integration_repositories.user_id,
    )
    await integration_repositories.rule_repo.save(rule)

    counter_account = await counter_account_resolution_service.resolve_counter_account(
        bank_transaction=transaction,
        account_repository=integration_repositories.account_repo,
    )

    assert counter_account is not None
    assert counter_account.id == groceries_account.id

    stored_rule = await integration_repositories.rule_repo.find_by_id(rule.id)
    assert stored_rule is not None
    assert stored_rule.match_count == 1


@pytest.mark.asyncio
async def test_transaction_import_service_imports_real_transaction(
    integration_repositories,
    bank_account_service,
    transaction_import_service,
    sample_account,
    sample_transactions,
):
    """End-to-end import should persist accounting transaction and stats."""

    transaction = next(
        (
            tx
            for tx in sample_transactions
            if _extract_keyword_from_transaction_purpose(tx.purpose)
        ),
        None,
    )
    if not transaction:
        pytest.skip("Need a transaction with a valid purpose to test import flow")

    keyword = _extract_keyword_from_transaction_purpose(transaction.purpose)
    if not keyword:
        pytest.skip("Unable to derive rule keyword from transaction purpose")

    # Ensure bank account and mapping exist prior to import
    user_id = integration_repositories.user_id
    await bank_account_service.import_bank_account(sample_account)

    account_repo = integration_repositories.account_repo
    category_account = await account_repo.find_by_account_number("4900")
    if not category_account:
        pytest.skip("Default 'Sonstiges' expense account (4900) missing")

    rule = CounterAccountRule(
        pattern_type=PatternType.PURPOSE_TEXT,
        pattern_value=keyword,
        counter_account_id=category_account.id,
        priority=250,
        source=RuleSource.USER_CREATED,
        user_id=user_id,
    )
    await integration_repositories.rule_repo.save(rule)

    result = await transaction_import_service.import_transaction(
        bank_transaction=transaction,
        source_iban=sample_account.iban,
    )

    assert result.is_success
    assert result.accounting_transaction is not None
    assert len(result.accounting_transaction.entries) == 2

    # Duplicate imports should be detected
    duplicate_result = await transaction_import_service.import_transaction(
        bank_transaction=transaction,
        source_iban=sample_account.iban,
    )
    assert duplicate_result.is_duplicate

    stats = await transaction_import_service.get_import_statistics(sample_account.iban)
    assert stats["success"] == 1
    # Duplicate imports reuse the same persisted record, so stats stay at 1
    assert stats["duplicate"] == 0
    assert stats["total"] == 1
