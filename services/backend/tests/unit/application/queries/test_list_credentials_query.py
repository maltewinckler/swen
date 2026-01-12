"""Unit tests for ListCredentialsQuery."""

from unittest.mock import AsyncMock

import pytest
from swen.application.queries import ListCredentialsQuery
from swen.domain.banking.value_objects import BankCredentials


class TestListCredentialsQuery:
    """Tests for the ListCredentialsQuery.

    Note: The credential repository is now user-scoped via UserContext,
    so query methods no longer take user_id parameters.
    """

    @pytest.fixture
    def mock_credential_repo(self):
        """Create a mock credential repository (user-scoped)."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_execute_returns_credentials_list(self, mock_credential_repo):
        """Test that execute returns a list of credentials."""
        mock_credential_repo.find_all.return_value = [
            ("cred-id-1", "12345678", "Bank A"),
            ("cred-id-2", "87654321", "Bank B"),
        ]

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.execute()

        assert result.total_count == 2
        assert len(result.credentials) == 2
        assert result.credentials[0].blz == "12345678"
        assert result.credentials[0].label == "Bank A"
        assert result.credentials[1].blz == "87654321"
        mock_credential_repo.find_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_returns_empty_list_when_no_credentials(
        self,
        mock_credential_repo,
    ):
        """Test that execute returns empty list when no credentials exist."""
        mock_credential_repo.find_all.return_value = []

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.execute()

        assert result.total_count == 0
        assert result.credentials == []

    @pytest.mark.asyncio
    async def test_execute_handles_none_label(self, mock_credential_repo):
        """Test that execute handles credentials with no label."""
        mock_credential_repo.find_all.return_value = [
            ("cred-id-1", "12345678", None),
        ]

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.execute()

        assert result.credentials[0].label == ""

    @pytest.mark.asyncio
    async def test_find_by_bank_code_returns_credentials(self, mock_credential_repo):
        """Test finding credentials by bank code."""
        mock_credentials = AsyncMock(spec=BankCredentials)
        mock_credential_repo.find_by_blz.return_value = mock_credentials

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.find_by_bank_code("12345678")

        assert result == mock_credentials
        mock_credential_repo.find_by_blz.assert_called_once_with("12345678")

    @pytest.mark.asyncio
    async def test_find_by_bank_code_returns_none_when_not_found(
        self,
        mock_credential_repo,
    ):
        """Test finding credentials returns None when not found."""
        mock_credential_repo.find_by_blz.return_value = None

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.find_by_bank_code("99999999")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_tan_settings_returns_tuple(self, mock_credential_repo):
        """Test getting TAN settings."""
        mock_credential_repo.get_tan_settings.return_value = ("946", "SecureGo")

        query = ListCredentialsQuery(mock_credential_repo)
        tan_method, tan_medium = await query.get_tan_settings("12345678")

        assert tan_method == "946"
        assert tan_medium == "SecureGo"
        mock_credential_repo.get_tan_settings.assert_called_once_with("12345678")

    @pytest.mark.asyncio
    async def test_get_tan_settings_returns_none_when_not_set(
        self,
        mock_credential_repo,
    ):
        """Test getting TAN settings when not configured."""
        mock_credential_repo.get_tan_settings.return_value = (None, None)

        query = ListCredentialsQuery(mock_credential_repo)
        tan_method, tan_medium = await query.get_tan_settings("12345678")

        assert tan_method is None
        assert tan_medium is None

    @pytest.mark.asyncio
    async def test_delete_returns_true_when_deleted(self, mock_credential_repo):
        """Test deleting credentials returns True on success."""
        mock_credential_repo.delete.return_value = True

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.delete("12345678")

        assert result is True
        mock_credential_repo.delete.assert_called_once_with("12345678")

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self, mock_credential_repo):
        """Test deleting credentials returns False when not found."""
        mock_credential_repo.delete.return_value = False

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.delete("99999999")

        assert result is False


class TestListCredentialsQueryDependencyInjection:
    """Tests to verify proper dependency injection."""

    def test_query_requires_repository(self):
        """Test that query requires a repository to be injected."""
        # Should be able to create with a mock repository
        mock_repo = AsyncMock()
        query = ListCredentialsQuery(mock_repo)
        assert query._credential_repo is mock_repo

    @pytest.mark.asyncio
    async def test_query_delegates_to_repository(self):
        """Test that query delegates all operations to the repository."""
        mock_repo = AsyncMock()
        mock_repo.find_all.return_value = []
        mock_repo.find_by_blz.return_value = None
        mock_repo.get_tan_settings.return_value = (None, None)
        mock_repo.delete.return_value = True

        query = ListCredentialsQuery(mock_repo)

        # All methods should delegate to repository (no user_id since repo is user-scoped)
        await query.execute()
        await query.find_by_bank_code("12345678")
        await query.get_tan_settings("12345678")
        await query.delete("12345678")

        assert mock_repo.find_all.called
        assert mock_repo.find_by_blz.called
        assert mock_repo.get_tan_settings.called
        assert mock_repo.delete.called
