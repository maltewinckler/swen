"""Unit tests for UpdateCredentialsCommand."""

from unittest.mock import AsyncMock

import pytest

from swen.application.banking.commands.credentials import UpdateCredentialsCommand
from swen.application.banking.dtos import UpdateCredentialsDTO
from swen.domain.banking.exceptions import CredentialsNotFoundError
from swen.domain.banking.value_objects import BankCredentials
from swen.domain.shared.value_objects import SecureString


@pytest.fixture
def mock_credential_repo():
    return AsyncMock()


@pytest.fixture
def mock_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


@pytest.fixture
def command(mock_credential_repo, mock_uow):
    return UpdateCredentialsCommand(
        credential_repository=mock_credential_repo,
        uow=mock_uow,
    )


def make_existing_creds() -> BankCredentials:
    return BankCredentials.from_plain(blz="50031000", username="user", pin="pin")


class TestUpdateCredentialsCommand:
    @pytest.mark.asyncio
    async def test_updates_tan_settings_success(
        self,
        command,
        mock_credential_repo,
    ):
        """Should update tan settings when credentials exist."""
        mock_credential_repo.find_by_blz.return_value = make_existing_creds()
        dto = UpdateCredentialsDTO(
            blz="50031000", tan_method="946", tan_medium="SecureGo"
        )

        await command.execute(dto)

        mock_credential_repo.find_by_blz.assert_called_once_with("50031000")
        mock_credential_repo.update.assert_called_once_with(
            blz="50031000",
            username=None,
            pin=None,
            tan_method="946",
            tan_medium="SecureGo",
        )

    @pytest.mark.asyncio
    async def test_updates_with_none_tan_medium(
        self,
        command,
        mock_credential_repo,
    ):
        """Should allow tan_medium to be None."""
        mock_credential_repo.find_by_blz.return_value = make_existing_creds()
        dto = UpdateCredentialsDTO(blz="50031000", tan_method="940", tan_medium=None)

        await command.execute(dto)

        call_kwargs = mock_credential_repo.update.call_args.kwargs
        assert call_kwargs["tan_method"] == "940"
        assert call_kwargs["tan_medium"] is None

    @pytest.mark.asyncio
    async def test_updates_username_and_pin(
        self,
        command,
        mock_credential_repo,
    ):
        """Should pass username and pin as SecureStrings when provided."""
        mock_credential_repo.find_by_blz.return_value = make_existing_creds()
        new_username = SecureString("new_user")
        new_pin = SecureString("new_pin")
        dto = UpdateCredentialsDTO(blz="50031000", username=new_username, pin=new_pin)

        await command.execute(dto)

        call_kwargs = mock_credential_repo.update.call_args.kwargs
        assert call_kwargs["username"] is new_username
        assert call_kwargs["pin"] is new_pin
        assert call_kwargs["tan_method"] is None
        assert call_kwargs["tan_medium"] is None

    @pytest.mark.asyncio
    async def test_skips_none_fields(
        self,
        command,
        mock_credential_repo,
    ):
        """Omitted fields should be passed as None (infrastructure skips them)."""
        mock_credential_repo.find_by_blz.return_value = make_existing_creds()
        dto = UpdateCredentialsDTO(blz="50031000", tan_method="946")

        await command.execute(dto)

        call_kwargs = mock_credential_repo.update.call_args.kwargs
        assert call_kwargs["username"] is None
        assert call_kwargs["pin"] is None
        assert call_kwargs["tan_method"] == "946"
        assert call_kwargs["tan_medium"] is None

    @pytest.mark.asyncio
    async def test_raises_when_credentials_not_found(
        self,
        command,
        mock_credential_repo,
    ):
        """Should raise CredentialsNotFoundError when no credentials exist for BLZ."""
        mock_credential_repo.find_by_blz.return_value = None
        dto = UpdateCredentialsDTO(blz="50031000", tan_method="946", tan_medium=None)

        with pytest.raises(CredentialsNotFoundError):
            await command.execute(dto)

        mock_credential_repo.update.assert_not_called()
