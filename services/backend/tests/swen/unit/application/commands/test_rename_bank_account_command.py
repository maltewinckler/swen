"""Unit tests for RenameBankAccountCommand."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID, uuid4

import pytest

from swen.application.accounting.dtos import BankAccountDTO
from swen.application.integration.commands import RenameBankAccountCommand
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.entities import AccountMapping
from swen.domain.shared.current_user import CurrentUser
from swen.domain.shared.exceptions import ValidationError

TEST_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
TEST_IBAN = "DE89370400440532013000"


def _make_current_user() -> CurrentUser:
    return CurrentUser(user_id=TEST_USER_ID, email="test@example.com")


def _make_asset_account(name: str = "DKB - Girokonto") -> Account:
    return Account(
        name=name,
        account_type=AccountType.ASSET,
        account_number=f"BA-{TEST_IBAN[-8:]}",
        user_id=TEST_USER_ID,
        iban=TEST_IBAN,
        default_currency=Currency("EUR"),
    )


def _make_mapping(account: Account, name: str | None = None) -> AccountMapping:
    return AccountMapping(
        iban=TEST_IBAN,
        accounting_account_id=account.id,
        account_name=name or account.name,
        user_id=TEST_USER_ID,
        is_active=True,
    )


class TestRenameBankAccountCommand:
    """Unit tests for RenameBankAccountCommand.execute."""

    def setup_method(self) -> None:
        self.account_repo = Mock()
        self.mapping_repo = Mock()
        self.mock_bank_account_repo = AsyncMock()
        self.current_user = _make_current_user()

        from swen.domain.integration.services import BankAccountImportService

        self.import_service = BankAccountImportService(
            account_repository=self.account_repo,
            mapping_repository=self.mapping_repo,
            current_user=self.current_user,
            bank_account_repository=self.mock_bank_account_repo,
        )
        self.command = RenameBankAccountCommand(import_service=self.import_service)

    @pytest.mark.asyncio
    async def test_execute_renames_account_and_returns_dto(self) -> None:
        """execute() renames account and mapping and returns a BankAccountDTO."""
        account = _make_asset_account("Old Name")
        mapping = _make_mapping(account, "Old Name")

        self.mapping_repo.find_by_iban = AsyncMock(return_value=mapping)
        self.account_repo.find_by_id = AsyncMock(return_value=account)
        self.account_repo.save = AsyncMock()
        self.mapping_repo.save = AsyncMock()

        result = await self.command.execute(iban=TEST_IBAN, new_name="New Name")

        assert isinstance(result, BankAccountDTO)
        assert result.name == "New Name"
        assert result.iban == TEST_IBAN
        self.account_repo.save.assert_called_once()
        self.mapping_repo.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_raises_when_no_mapping(self) -> None:
        """execute() raises ValueError when the IBAN has no mapping."""
        self.mapping_repo.find_by_iban = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="No account mapping found"):
            await self.command.execute(iban=TEST_IBAN, new_name="Any Name")

    @pytest.mark.asyncio
    async def test_execute_raises_when_account_not_found(self) -> None:
        """execute() raises ValueError when the mapped account no longer exists."""
        account = _make_asset_account()
        mapping = _make_mapping(account)
        mapping_with_gone_account = AccountMapping(
            iban=TEST_IBAN,
            accounting_account_id=uuid4(),
            account_name="Gone",
            user_id=TEST_USER_ID,
            is_active=True,
        )

        self.mapping_repo.find_by_iban = AsyncMock(
            return_value=mapping_with_gone_account
        )
        self.account_repo.find_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Mapping exists but account not found"):
            await self.command.execute(iban=TEST_IBAN, new_name="Any Name")

    @pytest.mark.asyncio
    async def test_execute_raises_on_empty_name(self) -> None:
        """execute() propagates ValidationError for an empty name."""
        account = _make_asset_account()
        mapping = _make_mapping(account)

        self.mapping_repo.find_by_iban = AsyncMock(return_value=mapping)
        self.account_repo.find_by_id = AsyncMock(return_value=account)

        with pytest.raises(ValidationError):
            await self.command.execute(iban=TEST_IBAN, new_name="")


class TestRenameBankAccountCommandFromFactory:
    """Tests that from_factory wires the command correctly."""

    def test_from_factory_creates_command(self) -> None:
        """from_factory should return a RenameBankAccountCommand."""
        factory = MagicMock()
        factory.current_user = _make_current_user()
        factory.account_repository.return_value = Mock()
        factory.account_mapping_repository.return_value = Mock()

        command = RenameBankAccountCommand.from_factory(factory)

        assert isinstance(command, RenameBankAccountCommand)
        factory.account_repository.assert_called_once()
        factory.account_mapping_repository.assert_called_once()
