"""Unit tests for SetupBankCommand."""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from swen.application.banking.commands import SetupBankCommand
from swen.application.banking.dtos import BankAccountToImportDTO, SetupBankRequestDTO
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.entities import AccountMapping

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


def _make_account_to_import_dto(
    iban: str = "DE89370400440532013000",
    custom_name: str | None = None,
) -> BankAccountToImportDTO:
    return BankAccountToImportDTO(
        iban=iban,
        default_name="Test Bank - Girokonto",
        account_number="532013000",
        account_holder="Max Mustermann",
        account_type="Girokonto",
        blz="37040044",
        bic="TESTDEFFXXX",
        bank_name="Test Bank",
        currency="EUR",
        custom_name=custom_name,
        balance="1000.00",
        balance_date="2024-01-01T00:00:00",
    )


class TestSetupBankCommand:
    """Test suite for SetupBankCommand."""

    @pytest.mark.asyncio
    async def test_successful_import_returns_dto_with_accounting_ids(self):
        """Importing accounts returns SetupBankResponseDTO with accounting_account_id set."""
        accounting_acct = Account(
            name="Test Bank - Girokonto",
            account_type=AccountType.ASSET,
            account_number="BA-32013000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )
        mapping = AccountMapping(
            iban="DE89370400440532013000",
            accounting_account_id=accounting_acct.id,
            account_name="Test Bank - Girokonto",
            user_id=TEST_USER_ID,
        )
        mock_import_service = AsyncMock()
        mock_import_service.import_bank_account.return_value = (
            accounting_acct,
            mapping,
        )

        command = SetupBankCommand(
            bank_fetch_service=AsyncMock(),
            import_service=mock_import_service,
            credential_repo=AsyncMock(),
        )
        request_dto = SetupBankRequestDTO(
            blz="37040044",
            accounts=[_make_account_to_import_dto()],
        )

        result = await command.execute(request_dto)

        assert result.success is True
        assert result.blz == "37040044"
        assert len(result.imported_accounts) == 1
        assert result.imported_accounts[0].iban == "DE89370400440532013000"
        assert result.imported_accounts[0].accounting_account_id == accounting_acct.id

    @pytest.mark.asyncio
    async def test_custom_name_is_forwarded_to_import_service(self):
        """custom_name from the DTO is passed through to BankAccountImportService."""
        accounting_acct = Account(
            name="Mein Konto",
            account_type=AccountType.ASSET,
            account_number="BA-32013000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )
        mock_import_service = AsyncMock()
        mock_import_service.import_bank_account.return_value = (
            accounting_acct,
            AsyncMock(),
        )

        command = SetupBankCommand(
            bank_fetch_service=AsyncMock(),
            import_service=mock_import_service,
            credential_repo=AsyncMock(),
        )
        request_dto = SetupBankRequestDTO(
            blz="37040044",
            accounts=[_make_account_to_import_dto(custom_name="Mein Konto")],
        )

        await command.execute(request_dto)

        _, call_kwargs = mock_import_service.import_bank_account.call_args
        assert call_kwargs["custom_name"] == "Mein Konto"

    @pytest.mark.asyncio
    async def test_multiple_accounts_all_imported(self):
        """All accounts in the request are imported and returned."""
        mock_import_service = AsyncMock()
        mock_import_service.import_bank_account.side_effect = [
            (
                Account(
                    name=f"Account {i}",
                    account_type=AccountType.ASSET,
                    account_number=f"BA-{i:08d}",
                    user_id=TEST_USER_ID,
                    default_currency=Currency("EUR"),
                ),
                AsyncMock(),
            )
            for i in range(3)
        ]

        command = SetupBankCommand(
            bank_fetch_service=AsyncMock(),
            import_service=mock_import_service,
            credential_repo=AsyncMock(),
        )
        accounts = [
            _make_account_to_import_dto(iban=f"DE{i:020d}") for i in range(1, 4)
        ]
        request_dto = SetupBankRequestDTO(blz="37040044", accounts=accounts)

        result = await command.execute(request_dto)

        assert result.success is True
        assert len(result.imported_accounts) == 3
        assert mock_import_service.import_bank_account.call_count == 3

    @pytest.mark.asyncio
    async def test_import_service_exception_propagates(self):
        """Exceptions from the import service bubble up so the router can rollback."""
        mock_import_service = AsyncMock()
        mock_import_service.import_bank_account.side_effect = ValueError(
            "IBAN already linked to a non-asset account"
        )

        command = SetupBankCommand(
            bank_fetch_service=AsyncMock(),
            import_service=mock_import_service,
            credential_repo=AsyncMock(),
        )
        request_dto = SetupBankRequestDTO(
            blz="37040044",
            accounts=[_make_account_to_import_dto()],
        )

        with pytest.raises(ValueError, match="IBAN already linked"):
            await command.execute(request_dto)

    @pytest.mark.asyncio
    async def test_result_is_serializable_as_dict(self):
        """SetupBankResponseDTO can be round-tripped via model_dump (used by router)."""
        accounting_acct = Account(
            name="Test Bank - Girokonto",
            account_type=AccountType.ASSET,
            account_number="BA-32013000",
            user_id=TEST_USER_ID,
            default_currency=Currency("EUR"),
        )
        mock_import_service = AsyncMock()
        mock_import_service.import_bank_account.return_value = (
            accounting_acct,
            AsyncMock(),
        )

        command = SetupBankCommand(
            bank_fetch_service=AsyncMock(),
            import_service=mock_import_service,
            credential_repo=AsyncMock(),
        )
        request_dto = SetupBankRequestDTO(
            blz="37040044",
            accounts=[_make_account_to_import_dto()],
        )

        result = await command.execute(request_dto)
        dumped = result.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["success"] is True
        assert dumped["blz"] == "37040044"
        assert dumped["imported_accounts"][0]["iban"] == "DE89370400440532013000"
