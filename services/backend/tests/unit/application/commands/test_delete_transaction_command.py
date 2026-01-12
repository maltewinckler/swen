"""Unit tests for DeleteTransactionCommand."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from swen.application.commands.accounting import DeleteTransactionCommand
from swen.domain.accounting.exceptions import TransactionNotFoundError
from swen.domain.shared.exceptions import BusinessRuleViolation


@pytest.fixture
def mock_transaction_repo():
    """Create a mock transaction repository."""
    repo = AsyncMock()
    repo.find_by_id = AsyncMock()
    repo.save = AsyncMock()
    repo.delete = AsyncMock()
    return repo


@pytest.fixture
def draft_transaction():
    """Create a mock draft (unposted) transaction."""
    txn = MagicMock()
    txn.id = uuid4()
    txn.is_posted = False
    txn.unpost = MagicMock()
    return txn


@pytest.fixture
def posted_transaction():
    """Create a mock posted transaction."""
    txn = MagicMock()
    txn.id = uuid4()
    txn.is_posted = True
    txn.unpost = MagicMock()
    return txn


class TestDeleteTransactionCommand:
    """Tests for DeleteTransactionCommand."""

    @pytest.mark.asyncio
    async def test_delete_draft_transaction(
        self, mock_transaction_repo, draft_transaction
    ):
        """Can delete a draft transaction without force."""
        mock_transaction_repo.find_by_id.return_value = draft_transaction

        command = DeleteTransactionCommand(mock_transaction_repo)
        await command.execute(transaction_id=draft_transaction.id)

        mock_transaction_repo.delete.assert_called_once_with(draft_transaction.id)
        # Should not call unpost for draft transactions
        draft_transaction.unpost.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_posted_transaction_without_force_raises(
        self, mock_transaction_repo, posted_transaction
    ):
        """Raises error when deleting posted transaction without force."""
        mock_transaction_repo.find_by_id.return_value = posted_transaction

        command = DeleteTransactionCommand(mock_transaction_repo)

        with pytest.raises(BusinessRuleViolation, match="Cannot delete posted"):
            await command.execute(transaction_id=posted_transaction.id, force=False)

        mock_transaction_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_posted_transaction_with_force(
        self, mock_transaction_repo, posted_transaction
    ):
        """Can delete posted transaction when force=True."""
        mock_transaction_repo.find_by_id.return_value = posted_transaction

        command = DeleteTransactionCommand(mock_transaction_repo)
        await command.execute(transaction_id=posted_transaction.id, force=True)

        # Should unpost first
        posted_transaction.unpost.assert_called_once()
        # Then save the unposted state
        mock_transaction_repo.save.assert_called_once_with(posted_transaction)
        # Then delete
        mock_transaction_repo.delete.assert_called_once_with(posted_transaction.id)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_transaction_raises(self, mock_transaction_repo):
        """Raises error when transaction not found."""
        mock_transaction_repo.find_by_id.return_value = None
        transaction_id = uuid4()

        command = DeleteTransactionCommand(mock_transaction_repo)

        with pytest.raises(TransactionNotFoundError):
            await command.execute(transaction_id=transaction_id)

        mock_transaction_repo.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_draft_transaction_force_does_not_unpost(
        self, mock_transaction_repo, draft_transaction
    ):
        """Force flag on draft transaction doesn't attempt unpost."""
        mock_transaction_repo.find_by_id.return_value = draft_transaction

        command = DeleteTransactionCommand(mock_transaction_repo)
        await command.execute(transaction_id=draft_transaction.id, force=True)

        # Should not unpost draft (it's already unposted)
        draft_transaction.unpost.assert_not_called()
        mock_transaction_repo.delete.assert_called_once_with(draft_transaction.id)

    def test_from_factory(self):
        """Can create command from factory."""
        mock_factory = MagicMock()
        mock_repo = AsyncMock()
        mock_factory.transaction_repository.return_value = mock_repo

        command = DeleteTransactionCommand.from_factory(mock_factory)

        assert isinstance(command, DeleteTransactionCommand)
        mock_factory.transaction_repository.assert_called_once()
