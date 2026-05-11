"""Unit tests for ListCredentialsQuery."""

from unittest.mock import AsyncMock

import pytest

from swen.application.queries import ListCredentialsQuery


class TestListCredentialsQuery:
    """Tests for the ListCredentialsQuery.

    Note: The credential repository is now user-scoped via CurrentUser,
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

        assert len(result.credentials) == 2
        assert result.credentials[0].credential_id == "cred-id-1"
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

        assert result.credentials == []

    @pytest.mark.asyncio
    async def test_execute_handles_none_label(self, mock_credential_repo):
        """Test that execute handles credentials with no label."""
        mock_credential_repo.find_all.return_value = [
            ("cred-id-1", "12345678", None),
        ]

        query = ListCredentialsQuery(mock_credential_repo)
        result = await query.execute()

        assert result.credentials[0].label is None


class TestListCredentialsQueryDependencyInjection:
    """Tests to verify proper dependency injection."""

    def test_query_requires_repository(self):
        """Test that query requires a repository to be injected."""
        # Should be able to create with a mock repository
        mock_repo = AsyncMock()
        query = ListCredentialsQuery(mock_repo)
        assert query._credential_repo is mock_repo
