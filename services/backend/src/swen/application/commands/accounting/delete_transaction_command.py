"""Delete accounting transactions, respecting draft state by default."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from swen.domain.accounting.exceptions import TransactionNotFoundError
from swen.domain.accounting.repositories import TransactionRepository
from swen.domain.shared.exceptions import BusinessRuleViolation

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory


class DeleteTransactionCommand:
    """Delete a transaction after validating its state."""

    def __init__(
        self,
        transaction_repository: TransactionRepository,
    ):
        self._transaction_repo = transaction_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> DeleteTransactionCommand:
        return cls(transaction_repository=factory.transaction_repository())

    async def execute(
        self,
        transaction_id: UUID,
        force: bool = False,
    ) -> None:
        # Load transaction (repo is user-scoped, ownership is guaranteed)
        transaction = await self._transaction_repo.find_by_id(transaction_id)
        if not transaction:
            raise TransactionNotFoundError(transaction_id)

        # Check if transaction is posted
        if transaction.is_posted:
            if not force:
                msg = (
                    f"Cannot delete posted transaction {transaction_id}. "
                    "Unpost the transaction first, or use force=True to delete anyway."
                )
                raise BusinessRuleViolation(msg)
            # Force mode: unpost before deletion (for audit trail in logs)
            transaction.unpost()
            await self._transaction_repo.save(transaction)

        # Delete the transaction
        await self._transaction_repo.delete(transaction_id)
