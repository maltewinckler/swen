"""Create new accounting accounts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

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


class CreateAccountCommand:
    """Validate and create a new account for the current user."""

    def __init__(
        self,
        account_repository: AccountRepository,
        account_hierarchy_service: AccountHierarchyService,
        current_user: CurrentUser,
    ):
        self._account_repo = account_repository
        self._account_hierarchy_service = account_hierarchy_service
        self._user_id = current_user.user_id

    @classmethod
    def from_factory(cls, factory: RepositoryFactory) -> CreateAccountCommand:
        return cls(
            account_repository=factory.account_repository(),
            account_hierarchy_service=AccountHierarchyService.from_factory(factory),
            current_user=factory.current_user,
        )

    async def execute(  # NOQA: PLR0913
        self,
        name: str,
        account_type: str,
        account_number: str,
        currency: str = "EUR",
        description: Optional[str] = None,
        parent_id: Optional[UUID] = None,
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

        return account
