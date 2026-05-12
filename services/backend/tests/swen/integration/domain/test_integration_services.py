"""Integration tests for integration domain services using real FinTS data."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from swen.application.accounting.commands import GenerateDefaultAccountsCommand
from swen.application.factories import BankImportTransactionFactory
from swen.application.integration.services import (
    TransactionImportService,
)
from swen.domain.accounting.services import OpeningBalanceService
from swen.domain.banking.value_objects.bank_credentials import BankCredentials
from swen.domain.integration.services import (
    BankAccountImportService,
    TransferReconciliationService,
)
from swen.domain.integration.value_objects import ResolvedCounterAccount
from swen.domain.shared.time import today_utc
from swen.infrastructure.banking.local_fints.adapter import GeldstromAdapter
from swen.infrastructure.persistence.sqlalchemy.repositories.accounting import (
    AccountRepositorySQLAlchemy,
    TransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.banking import (
    BankAccountRepositorySQLAlchemy,
    BankTransactionRepositorySQLAlchemy,
)
from swen.infrastructure.persistence.sqlalchemy.repositories.integration import (
    AccountMappingRepositorySQLAlchemy,
    TransactionImportRepositorySQLAlchemy,
)
from tests.external.conftest import (
    InMemoryFinTSConfigRepository,
    InMemoryFinTSEndpointRepository,
)

# Load .env from repository root so we share credentials with other integration tests
ROOT_DIR = Path(__file__).parent.parent.parent.parent
ENV_PATH = ROOT_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

# Skip this module unless integration tests explicitly enabled
pytestmark = pytest.mark.integration


def _skip_if_decoupled_tan_pending(exc: Exception) -> None:
    if "Decoupled TAN challenge pending" in str(exc):
        pytest.skip(
            "Real FinTS integration fixture requires decoupled TAN approval for "
            "this bank; covered by the manual TAN suite.",
        )


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
def fints_endpoint_repo():
    """In-memory endpoint repo seeded from FINTS_ENDPOINT env var."""
    blz = os.getenv("FINTS_BLZ", "")
    endpoint = os.getenv("FINTS_ENDPOINT", "")
    return InMemoryFinTSEndpointRepository({blz: endpoint})


@pytest.fixture(scope="module")
def fints_config_repo():
    """In-memory FinTS config repo seeded from FINTS_PRODUCT_ID env var."""
    product_id = os.getenv("FINTS_PRODUCT_ID")
    if not product_id:
        pytest.skip(
            "Missing FINTS_PRODUCT_ID in .env. Required for adapter to connect.",
        )
    return InMemoryFinTSConfigRepository(product_id=product_id)


@pytest.fixture(scope="module")
async def connected_adapter(
    credentials,
    tan_settings,
    fints_endpoint_repo,
    fints_config_repo,
):
    """Provide a connected Geldstrom adapter for fetching real data."""

    adapter = GeldstromAdapter(
        config_repository=fints_config_repo,
        fints_endpoint_repo=fints_endpoint_repo,
    )
    adapter.set_tan_method(tan_settings["tan_method"])
    adapter.set_tan_medium(tan_settings["tan_medium"])

    try:
        try:
            connected = await adapter.connect(credentials)
        except Exception as exc:
            _skip_if_decoupled_tan_pending(exc)
            raise
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
    bank_account_repo = BankAccountRepositorySQLAlchemy(db_session, current_user)
    bank_transaction_repo = BankTransactionRepositorySQLAlchemy(
        db_session,
        current_user,
    )
    # Use the command instead of the deprecated domain service
    generate_accounts_cmd = GenerateDefaultAccountsCommand(
        account_repository=account_repo,
        current_user=current_user,
    )
    await generate_accounts_cmd.execute()

    yield SimpleNamespace(
        session=db_session,
        account_repo=account_repo,
        bank_account_repo=bank_account_repo,
        bank_transaction_repo=bank_transaction_repo,
        transaction_repo=TransactionRepositorySQLAlchemy(
            db_session,
            account_repo,
            current_user,
        ),
        mapping_repo=AccountMappingRepositorySQLAlchemy(db_session, current_user),
        import_repo=TransactionImportRepositorySQLAlchemy(db_session, current_user),
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
        bank_account_repository=integration_repositories.bank_account_repo,
    )


@pytest.fixture
def transaction_import_service(
    integration_repositories,
    bank_account_service,
):
    """Full transaction import orchestration service."""
    ob_service = OpeningBalanceService(
        account_repository=integration_repositories.account_repo,
        transaction_repository=integration_repositories.transaction_repo,
        user_id=integration_repositories.current_user.user_id,
    )

    transfer_reconciliation_service = TransferReconciliationService(
        transaction_repository=integration_repositories.transaction_repo,
    )

    transaction_factory = BankImportTransactionFactory(
        current_user=integration_repositories.current_user,
    )

    return TransactionImportService(
        bank_account_import_service=bank_account_service,
        transfer_reconciliation_service=transfer_reconciliation_service,
        opening_balance_service=ob_service,
        transaction_factory=transaction_factory,
        account_repository=integration_repositories.account_repo,
        transaction_repository=integration_repositories.transaction_repo,
        import_repository=integration_repositories.import_repo,
        current_user=integration_repositories.current_user,
    )


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

    assert asset_account.account_number == f"BA-{sample_account.iban[-8:]}"
    assert asset_account.iban == sample_account.iban
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
async def test_transaction_import_service_imports_real_transaction(
    integration_repositories,
    bank_account_service,
    transaction_import_service,
    sample_account,
    sample_transactions,
):
    """End-to-end import should persist accounting transaction and stats."""

    transaction = next(
        (tx for tx in sample_transactions if tx.purpose),
        None,
    )
    if not transaction:
        pytest.skip("Need a transaction with a valid purpose to test import flow")

    # Ensure bank account and mapping exist prior to import
    user_id = integration_repositories.user_id
    asset_account, _ = await bank_account_service.import_bank_account(sample_account)

    await integration_repositories.bank_account_repo.save(sample_account)
    stored_transaction = (
        await integration_repositories.bank_transaction_repo.save_batch_with_deduplication(
            [transaction],
            sample_account.iban,
        )
    )[0]

    resolved = {
        stored_transaction.id: ResolvedCounterAccount(
            account=asset_account,
            confidence=None,
        ),
    }

    results = await transaction_import_service.import_batch(
        stored_transactions=[stored_transaction],
        source_iban=sample_account.iban,
        resolved=resolved,
        auto_post=False,
    )
    result = results[0]

    assert result.is_success
    assert result.accounting_transaction is not None
    assert len(result.accounting_transaction.entries) == 2

    # Duplicate imports should be detected for the same stored transaction ID
    duplicate_results = await transaction_import_service.import_batch(
        stored_transactions=[stored_transaction],
        source_iban=sample_account.iban,
        resolved=resolved,
        auto_post=False,
    )
    duplicate_result = duplicate_results[0]

    assert duplicate_result.is_duplicate

    stats = await transaction_import_service.get_import_statistics(sample_account.iban)
    assert stats["success"] == 1
    # Duplicate imports reuse the same persisted record, so stats stay at 1
    assert stats["duplicate"] == 0
    assert stats["total"] == 1
