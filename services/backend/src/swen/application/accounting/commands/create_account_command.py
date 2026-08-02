"""Create new accounting accounts."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from swen.application.accounting.dtos.chart_of_accounts_dto import CreateAccountDTO
from swen.application.ports.account_classifier_training import AccountForClassification
from swen.application.ports.unit_of_work import UnitOfWork
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
    from swen.application.ports.account_classifier_training import (
        AccountClassifierTrainingPort,
    )
    from swen.domain.shared.current_user import CurrentUser

logger = logging.getLogger(__name__)


class CreateAccountCommand:
    """Validate and create a new account for the current user."""

    def __init__(
        self,
        account_repository: AccountRepository,
        account_hierarchy_service: AccountHierarchyService,
        current_user: CurrentUser,
        uow: UnitOfWork,
        ml_port: AccountClassifierTrainingPort | None = None,
    ):
        self._account_repo = account_repository
        self._account_hierarchy_service = account_hierarchy_service
        self._user_id = current_user.user_id
        self._uow = uow
        self._ml_port = ml_port

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
        ml_port: AccountClassifierTrainingPort | None = None,
    ) -> CreateAccountCommand:
        return cls(
            account_repository=factory.account_repository(),
            account_hierarchy_service=AccountHierarchyService.from_factory(factory),
            current_user=factory.current_user,
            uow=factory.unit_of_work(),
            ml_port=ml_port,
        )

    async def execute(self, dto: CreateAccountDTO) -> Account:
        try:
            acc_type = AccountType(dto.account_type.lower())
        except ValueError as e:
            valid_types = [t.value for t in AccountType]
            raise InvalidAccountTypeError(dto.account_type, valid_types) from e

        # Validate currency
        try:
            curr = Currency(dto.currency.upper())
        except ValueError as e:
            valid_currencies = sorted(SUPPORTED_CURRENCIES)
            raise InvalidCurrencyError(dto.currency, valid_currencies) from e

        async with self._uow:
            # Check for existing account with same number (repository is user-scoped)
            existing = await self._account_repo.find_by_account_number(
                dto.account_number
            )
            if existing:
                raise AccountAlreadyExistsError(
                    account_number=dto.account_number,
                    message=(
                        f"Account with number '{dto.account_number}' already exists"
                    ),
                )

            # Check for existing account with same name
            existing_name = await self._account_repo.find_by_name(dto.name)
            if existing_name:
                raise AccountAlreadyExistsError(
                    account_name=dto.name,
                    message=f"Account with name '{dto.name}' already exists",
                )

            # Create account with user_id from context
            account = Account(
                name=dto.name,
                account_type=acc_type,
                account_number=dto.account_number,
                default_currency=curr,
                user_id=self._user_id,
                description=dto.description,
            )

            # Validate and set parent with business rules
            if dto.parent_id:
                parent = await self._account_repo.find_by_id(dto.parent_id)
                if not parent:
                    raise AccountNotFoundError(account_id=dto.parent_id)

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
        # Only for expense/income accounts (used for classification)
        if account.account_type.value.lower() in ("expense", "income"):
            self._trigger_account_embedding(account)

        return account

    def _trigger_account_embedding(self, account: Account) -> None:
        """Trigger ML service to embed this account's anchor for classification."""
        if not self._ml_port:
            return

        accounts = [
            AccountForClassification(
                account_id=account.id,
                account_number=account.account_number,
                name=account.name,
                account_type=account.account_type.value.lower(),
                description=account.description,
            )
        ]
        self._ml_port.embed_accounts_fire_and_forget(self._user_id, accounts)
