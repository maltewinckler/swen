"""Unit tests for StoreCredentialsCommand."""

from unittest.mock import AsyncMock

import pytest

from swen.application.banking.commands import StoreCredentialsCommand
from swen.application.banking.dtos.credentials_dto import CredentialToStoreDTO
from swen.domain.banking.exceptions import CredentialsAlreadyExistError
from swen.domain.banking.value_objects import BankCredentials
from swen.domain.shared.value_objects import SecureString


@pytest.fixture
def mock_credential_repo():
    """Mock credential repository (user-scoped)."""
    return AsyncMock()


@pytest.fixture
def mock_uow():
    """No-op UnitOfWork for unit tests (no DB session needed)."""
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)
    return uow


@pytest.fixture
def command(mock_credential_repo, mock_uow):
    """Create command with mocked repository and UoW."""
    return StoreCredentialsCommand(
        credential_repository=mock_credential_repo,
        uow=mock_uow,
    )


def make_dto(
    blz: str = "50031000",
    username: str = "testuser",
    pin: str = "testpin",
    tan_method: str | None = None,
    tan_medium: str | None = None,
) -> CredentialToStoreDTO:
    return CredentialToStoreDTO(
        blz=blz,
        username=SecureString(username),
        pin=SecureString(pin),
        tan_method=tan_method,
        tan_medium=tan_medium,
    )


class TestStoreCredentialsCommand:
    """Test StoreCredentialsCommand."""

    @pytest.mark.asyncio
    async def test_store_new_credentials_success(
        self,
        command,
        mock_credential_repo,
    ):
        """Should store credentials when none exist."""
        dto = make_dto()
        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.return_value = "cred-id-123"

        result = await command.execute(dto)

        assert result == "cred-id-123"
        mock_credential_repo.find_by_blz.assert_called_once_with("50031000")
        mock_credential_repo.save.assert_called_once()
        call_kwargs = mock_credential_repo.save.call_args.kwargs
        assert call_kwargs["label"] == "50031000"
        assert call_kwargs["tan_method"] is None
        assert call_kwargs["tan_medium"] is None

    @pytest.mark.asyncio
    async def test_store_credentials_without_label(
        self,
        command,
        mock_credential_repo,
    ):
        """Should store credentials, using BLZ as label by default."""
        dto = make_dto()
        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.return_value = "cred-id-456"

        result = await command.execute(dto)

        assert result == "cred-id-456"
        call_kwargs = mock_credential_repo.save.call_args.kwargs
        assert call_kwargs["label"] == "50031000"

    @pytest.mark.asyncio
    async def test_store_credentials_with_tan_settings(
        self,
        command,
        mock_credential_repo,
    ):
        """Should store credentials with TAN settings."""
        dto = make_dto(tan_method="946", tan_medium="SecureGo")
        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.return_value = "cred-id-789"

        result = await command.execute(dto)

        assert result == "cred-id-789"
        call_kwargs = mock_credential_repo.save.call_args.kwargs
        assert call_kwargs["tan_method"] == "946"
        assert call_kwargs["tan_medium"] == "SecureGo"

    @pytest.mark.asyncio
    async def test_raises_error_when_credentials_exist(
        self,
        command,
        mock_credential_repo,
    ):
        """Should raise error when credentials already exist for user/BLZ."""
        dto = make_dto()
        existing_creds = BankCredentials.from_plain(
            blz="50031000",
            username="olduser",
            pin="oldpin",
        )
        mock_credential_repo.find_by_blz.return_value = existing_creds

        with pytest.raises(CredentialsAlreadyExistError):
            await command.execute(dto)

        mock_credential_repo.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_stores_credentials_for_multiple_banks(
        self,
        command,
        mock_credential_repo,
    ):
        """Should allow storing credentials for different banks."""
        triodos_dto = make_dto(
            blz="50031000", username="triodos_user", pin="triodos_pin"
        )
        dkb_dto = make_dto(blz="12030000", username="dkb_user", pin="dkb_pin")

        mock_credential_repo.find_by_blz.return_value = None
        mock_credential_repo.save.side_effect = ["cred-id-1", "cred-id-2"]

        result1 = await command.execute(triodos_dto)
        result2 = await command.execute(dkb_dto)

        assert result1 == "cred-id-1"
        assert result2 == "cred-id-2"
        assert mock_credential_repo.save.call_count == 2
