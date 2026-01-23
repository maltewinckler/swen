"""Create new accounting accounts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from swen_ml_contracts import AccountOption

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import (
    AccountAlreadyExistsError,
    AccountNotFoundError,
    InvalidAccountTypeError,
    InvalidCurrencyError,
)
from swen.domain.accounting.repositories import AccountRepository
from swen.domain.accounting.services import AccountHierarchyService
from swen.domain.accounting.value_objects import Currency
from swen.domain.accounting.value_objects.currency import SUPPORTED_CURRENCIES

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.application.ports.identity import CurrentUser
    from swen.infrastructure.integration.ml.client import MLServiceClient

logger = logging.getLogger(__name__)


class CreateAccountCommand:
    """Validate and create a new account for the current user."""

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
    ) -> CreateAccountCommand:
        return cls(
            account_repository=factory.account_repository(),
            account_hierarchy_service=AccountHierarchyService.from_factory(factory),
            current_user=factory.current_user,
            ml_client=ml_client,
        )

    async def execute(  # noqa: PLR0913
        self,
        name: str,
        account_type: str,
        account_number: str,
        currency: str = "EUR",
        description: str | None = None,
        parent_id: UUID | None = None,
    ) -> Account:
        try:
            acc_type = AccountType(account_type.lower())
        except ValueError as e:
            valid_types = [t.value for t in AccountType]
            raise InvalidAccountTypeError(account_type, valid_types) from e

        # Validate currency
        try:
            curr = Currency(currency.upper())
        except ValueError as e:
            valid_currencies = sorted(SUPPORTED_CURRENCIES)
            raise InvalidCurrencyError(currency, valid_currencies) from e

        # Check for existing account with same number (repository is user-scoped)
        existing = await self._account_repo.find_by_account_number(account_number)
        if existing:
            raise AccountAlreadyExistsError(
                account_number=account_number,
                message=f"Account with number '{account_number}' already exists",
            )

        # Check for existing account with same name
        existing_name = await self._account_repo.find_by_name(name)
        if existing_name:
            raise AccountAlreadyExistsError(
                account_name=name,
                message=f"Account with name '{name}' already exists",
            )

        # Create account with user_id from context
        account = Account(
            name=name,
            account_type=acc_type,
            account_number=account_number,
            default_currency=curr,
            user_id=self._user_id,
            description=description,
        )

        # Validate and set parent with business rules
        if parent_id:
            parent = await self._account_repo.find_by_id(parent_id)
            if not parent:
                raise AccountNotFoundError(account_id=parent_id)

            # Use domain method (with validation)
            account.set_parent(parent)

            # Validate hierarchy constraints via domain service
            if self._account_hierarchy_service:
                await self._account_hierarchy_service.validate_hierarchy(
                    child=account,
                    parent=parent,
                )

        # Save account
        await self._account_repo.save(account)

        # Trigger ML account embedding (fire-and-forget)
        self._trigger_account_embedding(account)

        return account

    def _trigger_account_embedding(self, account: Account) -> None:
        """Trigger ML service to embed account anchor for classification."""
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
