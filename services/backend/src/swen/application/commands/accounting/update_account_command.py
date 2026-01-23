"""Update or deactivate accounting accounts."""

from __future__ import annotations

import logging
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from swen_ml_contracts import AccountOption

from swen.domain.accounting.entities import Account
from swen.domain.accounting.exceptions import (
    AccountAlreadyExistsError,
    AccountCannotBeDeactivatedError,
    AccountNotFoundError,
)
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.accounting.services import AccountHierarchyService

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.identity import CurrentUser
    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class ParentAction(str, Enum):
    """Action to take on the account's parent relationship."""

    KEEP = "keep"
    SET = "set"
    REMOVE = "remove"


class UpdateAccountCommand:
    """Update account metadata and parent relationships."""

    def __init__(
        self,
        account_repository: AccountRepository,
        account_hierarchy_service: AccountHierarchyService,
        current_user: CurrentUser,
        ml_client: MLServiceClient | None = None,
    ):
        self._account_repo = account_repository
        self._account_hierarchy_service = account_hierarchy_service
        self._user_id = current_user.user_id
        self._ml_client = ml_client

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_client: MLServiceClient | None = None,
    ) -> UpdateAccountCommand:
        return cls(
            account_repository=factory.account_repository(),
            account_hierarchy_service=AccountHierarchyService.from_factory(factory),
            current_user=factory.current_user,
            ml_client=ml_client,
        )

    async def execute(  # noqa: PLR0913
        self,
        account_id: UUID,
        name: str | None = None,
        account_number: str | None = None,
        description: str | None = None,
        parent_id: UUID | None = None,
        parent_action: ParentAction = ParentAction.KEEP,
    ) -> Account:
        account = await self._get_account(account_id)

        if name is not None:
            await self._update_name(account, name)

        if account_number is not None:
            await self._update_account_number(account, account_number)

        if description is not None:
            account.set_description(description)

        await self._handle_parent_action(account, parent_id, parent_action)

        await self._account_repo.save(account)

        # Trigger ML account embedding update (fire-and-forget)
        self._trigger_account_embedding(account)

        return account

    def _trigger_account_embedding(self, account: Account) -> None:
        """Trigger ML service to re-embed account anchor for classification."""
        if not self._ml_client:
            return

        # Only embed expense/income accounts (used for classification)
        if account.account_type.value.lower() not in ("expense", "income"):
            return

        accounts = [
            AccountOption(
                account_id=account.id,
                account_number=account.account_number,
                name=account.name,
                account_type=account.account_type.value.lower(),  # type: ignore[arg-type]
                description=account.description,
            )
        ]
        self._ml_client.embed_accounts_fire_and_forget(self._user_id, accounts)

    async def _get_account(self, account_id: UUID) -> Account:
        account = await self._account_repo.find_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(account_id=account_id)
        return account

    async def _update_name(self, account: Account, name: str) -> None:
        existing = await self._account_repo.find_by_name(name)
        if existing is not None and existing.id != account.id:
            raise AccountAlreadyExistsError(
                account_name=name,
                message=f"Account with name '{name}' already exists",
            )
        account.rename(name)

    async def _update_account_number(
        self,
        account: Account,
        account_number: str,
    ) -> None:
        existing = await self._account_repo.find_by_account_number(account_number)
        if existing is not None and existing.id != account.id:
            raise AccountAlreadyExistsError(
                account_number=account_number,
                message=f"Account with number '{account_number}' already exists",
            )
        account.change_account_number(account_number)

    async def _handle_parent_action(
        self,
        account: Account,
        parent_id: UUID | None,
        parent_action: ParentAction,
    ) -> None:
        if parent_action == ParentAction.SET:
            await self._set_parent(account, parent_id)
        elif parent_action == ParentAction.REMOVE:
            account.remove_parent()
        # ParentAction.KEEP: do nothing, preserve current parent

    async def _set_parent(self, account: Account, parent_id: UUID | None) -> None:
        if parent_id is None:
            msg = "parent_id is required when parent_action is 'set'"
            raise ValueError(msg)

        parent = await self._account_repo.find_by_id(parent_id)
        if not parent:
            raise AccountNotFoundError(account_id=parent_id)

        account.set_parent(parent)

        if self._account_hierarchy_service:
            await self._account_hierarchy_service.validate_hierarchy(
                child=account,
                parent=parent,
            )


class DeactivateAccountCommand:
    """Deactivate an account (soft delete)."""

    def __init__(
        self,
        account_repository: AccountRepository,
        account_hierarchy_service: AccountHierarchyService,
    ):
        self._account_repo = account_repository
        self._account_hierarchy_service = account_hierarchy_service

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> DeactivateAccountCommand:
        return cls(
            account_repository=factory.account_repository(),
            account_hierarchy_service=AccountHierarchyService.from_factory(factory),
        )

    async def execute(self, account_id: UUID) -> Account:
        account = await self._account_repo.find_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(account_id=account_id)

        if not await self._account_hierarchy_service.can_delete(account):
            raise AccountCannotBeDeactivatedError(account.name)
        account.deactivate()
        await self._account_repo.save(account)
        return account


class ReactivateAccountCommand:
    """Command to reactivate a deactivated account."""

    def __init__(self, account_repository: AccountRepository):
        self._account_repo = account_repository

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> ReactivateAccountCommand:
        return cls(account_repository=factory.account_repository())

    async def execute(self, account_id: UUID) -> Account:
        account = await self._account_repo.find_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(account_id=account_id)

        account.activate()
        await self._account_repo.save(account)
        return account


class DeleteAccountCommand:
    """Command to permanently delete an account."""

    def __init__(
        self,
        account_repository: AccountRepository,
        account_hierarchy_service: AccountHierarchyService,
    ):
        self._account_repo = account_repository
        self._account_hierarchy_service = account_hierarchy_service

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> DeleteAccountCommand:
        return cls(
            account_repository=factory.account_repository(),
            account_hierarchy_service=AccountHierarchyService.from_factory(factory),
        )

    async def execute(self, account_id: UUID) -> None:
        account = await self._account_repo.find_by_id(account_id)
        if account is None:
            raise AccountNotFoundError(account_id=account_id)

        if not await self._account_hierarchy_service.can_delete(account):
            raise AccountCannotBeDeactivatedError(account.name)

        await self._account_repo.delete(account_id)
