"""Create an external account and IBAN mapping for non-FinTS institutions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from swen.application.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)
from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError, InvalidCurrencyError
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.exceptions import InvalidIbanError
from swen.domain.shared.exceptions import ValidationError
from swen.domain.shared.iban import normalize_iban

if TYPE_CHECKING:
    from swen.application.ports.identity import CurrentUser
    from swen.application.factories import RepositoryFactory
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.domain.integration.repositories import AccountMappingRepository


@dataclass
class CreateExternalAccountResult:
    """Result of creating an external account mapping."""

    account: Account
    mapping: AccountMapping
    transactions_reconciled: int
    already_existed: bool


class CreateExternalAccountCommand:
    """Create an external account + mapping and optionally reconcile history."""

    def __init__(
        self,
        account_repository: AccountRepository,
        mapping_repository: AccountMappingRepository,
        transaction_repository: TransactionRepository,
        current_user: CurrentUser,
    ):
        self._account_repo = account_repository
        self._mapping_repo = mapping_repository
        self._transaction_repo = transaction_repository
        self._current_user = current_user

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> CreateExternalAccountCommand:
        return cls(
            account_repository=factory.account_repository(),
            mapping_repository=factory.account_mapping_repository(),
            transaction_repository=factory.transaction_repository(),
            current_user=factory.current_user,
        )

    async def execute(
        self,
        iban: str,
        name: str,
        currency: str = "EUR",
        account_type: AccountType = AccountType.ASSET,
        reconcile: bool = True,
    ) -> CreateExternalAccountResult:
        normalized_iban = normalize_iban(iban) or ""
        if not normalized_iban:
            raise InvalidIbanError(iban, "IBAN cannot be empty")

        try:
            curr = Currency(currency.upper())
        except ValueError as e:
            raise InvalidCurrencyError(currency) from e

        allowed_types = (AccountType.ASSET, AccountType.LIABILITY)
        if account_type not in allowed_types:
            msg = f"account_type must be ASSET or LIABILITY, got {account_type.value}"
            raise ValidationError(msg)

        existing_mapping = await self._mapping_repo.find_by_iban(normalized_iban)

        if existing_mapping is not None:
            existing_account = await self._account_repo.find_by_id(
                existing_mapping.accounting_account_id,
            )
            if existing_account is None:
                raise AccountNotFoundError(
                    account_id=existing_mapping.accounting_account_id,
                )
            return CreateExternalAccountResult(
                account=existing_account,
                mapping=existing_mapping,
                transactions_reconciled=0,
                already_existed=True,
            )

        existing_account_by_iban = await self._account_repo.find_by_iban(
            normalized_iban,
        )
        if existing_account_by_iban is not None:
            if existing_account_by_iban.account_type != account_type:
                msg = (
                    f"Found existing account for IBAN {normalized_iban} but it is "
                    f"{existing_account_by_iban.account_type.value}, "
                    f"not {account_type.value}"
                )
                raise ValidationError(msg)

            mapping = AccountMapping(
                iban=normalized_iban,
                accounting_account_id=existing_account_by_iban.id,
                account_name=name,
                user_id=self._current_user.user_id,
                is_active=True,
            )
            await self._mapping_repo.save(mapping)

            reconciled_count = 0
            if reconcile:
                reconciled_count = await self._reconcile_transactions(
                    normalized_iban,
                    existing_account_by_iban,
                    account_type,
                )

            return CreateExternalAccountResult(
                account=existing_account_by_iban,
                mapping=mapping,
                transactions_reconciled=reconciled_count,
                already_existed=True,  # Account existed, mapping was new
            )

        prefix = "LIA" if account_type == AccountType.LIABILITY else "EXT"
        account_number = f"{prefix}-{normalized_iban[-8:]}"

        new_account = Account(
            name=name,
            account_type=account_type,
            account_number=account_number,
            user_id=self._current_user.user_id,
            iban=normalized_iban,
            default_currency=curr,
        )

        # Save the account
        await self._account_repo.save(new_account)

        # Create mapping
        mapping = AccountMapping(
            iban=normalized_iban,
            accounting_account_id=new_account.id,
            account_name=name,
            user_id=self._current_user.user_id,
            is_active=True,
        )

        # Save the mapping
        await self._mapping_repo.save(mapping)

        # Optionally reconcile existing transactions
        reconciled_count = 0
        if reconcile:
            reconciled_count = await self._reconcile_transactions(
                normalized_iban,
                new_account,
                account_type,
            )

        return CreateExternalAccountResult(
            account=new_account,
            mapping=mapping,
            transactions_reconciled=reconciled_count,
            already_existed=False,
        )

    async def _reconcile_transactions(
        self,
        iban: str,
        account: Account,
        account_type: AccountType,
    ) -> int:
        reconciliation_service = TransferReconciliationService(
            transaction_repository=self._transaction_repo,
            mapping_repository=self._mapping_repo,
            account_repository=self._account_repo,
        )

        if account_type == AccountType.ASSET:
            return await reconciliation_service.reconcile_for_new_account(
                iban=iban,
                asset_account=account,
            )
        if account_type == AccountType.LIABILITY:
            return await reconciliation_service.reconcile_liability_for_new_account(
                iban=iban,
                liability_account=account,
            )

        return 0
