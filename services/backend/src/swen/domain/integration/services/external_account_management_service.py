"""Domain service for managing external (non-FinTS) bank accounts.

Handles creation and lookup of external accounts — accounts at institutions
that do not offer FinTS access. This includes stock portfolios, foreign banks,
credit cards, and loans.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from swen.domain.accounting.entities import Account, AccountType
from swen.domain.accounting.exceptions import AccountNotFoundError, InvalidCurrencyError
from swen.domain.accounting.value_objects import Currency
from swen.domain.integration.entities import AccountMapping
from swen.domain.integration.exceptions import InvalidIbanError
from swen.domain.integration.services.transfer_reconciliation_service import (
    TransferReconciliationService,
)
from swen.domain.shared.exceptions import ValidationError
from swen.domain.shared.iban import normalize_iban

if TYPE_CHECKING:
    from swen.domain.accounting.entities import Account
    from swen.domain.accounting.repositories import (
        AccountRepository,
        TransactionRepository,
    )
    from swen.domain.integration.entities import AccountMapping
    from swen.domain.integration.repositories import AccountMappingRepository
    from swen.domain.shared.current_user import CurrentUser

logger = logging.getLogger(__name__)


# Very tiny scoped class that is only used to internally carry data
# It should not be exposed to the presentation layer
@dataclass(frozen=True)
class ExternalAccountResult:
    """Result of creating or finding an external account.

    This is a domain-level value object that carries the result of
    external account operations from the domain service back to the
    application layer.
    """

    account: Account
    mapping: AccountMapping
    transactions_reconciled: int
    already_existed: bool


class ExternalAccountManagementService:
    """Manage external (non-FinTS) bank accounts and their mappings.

    Business rules:
    - External accounts are for institutions without FinTS access
    - Account numbers follow pattern: EXT-{last8} for assets, LIA-{last8} for liability
    - If mapping exists → return existing (with orphan check)
    - If account exists by IBAN → create mapping only
    - Otherwise → create both account and mapping
    """

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

    def generate_account_number(self, iban: str, account_type: AccountType) -> str:
        """Generate account number based on type.

        Returns EXT-{last8} for ASSET accounts, LIA-{last8} for LIABILITY.
        """
        prefix = "LIA" if account_type == AccountType.LIABILITY else "EXT"
        return f"{prefix}-{iban[-8:]}"

    def _normalize_iban(self, iban: str | None) -> str:
        """Normalize and validate IBAN."""
        normalized = normalize_iban(iban)
        if not normalized:
            placeholder = ""
            raise InvalidIbanError(placeholder, "IBAN cannot be empty")
        return normalized

    def _validate_currency(self, currency: str) -> Currency:
        """Validate and create Currency value object."""
        try:
            return Currency(currency.upper())
        except ValueError as e:
            raise InvalidCurrencyError(currency) from e

    async def create_or_find_external_account(
        self,
        iban: str,
        name: str,
        currency: str,
        account_type: AccountType,
        reconcile: bool = True,
    ) -> ExternalAccountResult:
        """Create external account + mapping, or find existing.

        This is the core business method that encapsulates the three-scenario
        orchestration for external account management.

        Args:
            iban: Normalized IBAN of the external bank account.
            name: Display name for the account.
            currency: Currency for the account.
            account_type: ASSET or LIABILITY.
            reconcile: Whether to reconcile existing transactions.

        Returns
        -------
            ExternalAccountResult with account, mapping, reconciled count,
            and already_existed flag.

        Raises
        ------
            InvalidIbanError: If IBAN is empty.
            ValidationError: If account type is invalid or type mismatch.
            AccountNotFoundError: If mapping exists but referenced account is missing.
        """
        norm_iban = self._normalize_iban(iban)
        norm_currency = self._validate_currency(currency)

        allowed_types = (AccountType.ASSET, AccountType.LIABILITY)
        if account_type not in allowed_types:
            raise ValidationError(
                "account_type must be ASSET or LIABILITY, got %s" % account_type.value
            )

        # Scenario 1: If mapping already exists, return existing
        existing_mapping = await self._mapping_repo.find_by_iban(norm_iban)
        if existing_mapping is not None:
            return await self._handle_existing_mapping(existing_mapping)

        # Scenario 2: If Account exists by IBAN, create mapping only
        # This should be dead code because mappings should be created
        # as soon as we have an IBAN (mostly fints, but also scenario 3)
        # But we keep this as a safety net.
        existing_account = await self._account_repo.find_by_iban(norm_iban)
        if existing_account is not None:
            return await self._handle_existing_account(
                existing_account,
                name=name,
                reconcile=reconcile,
                account_type=account_type,
            )

        # Scenario 3: If not existing account or mapping, create both
        return await self._handle_new_account(
            iban=norm_iban,
            name=name,
            currency=norm_currency,
            account_type=account_type,
            reconcile=reconcile,
        )

    async def _handle_existing_mapping(
        self,
        mapping: AccountMapping,
    ) -> ExternalAccountResult:
        """Handle case where a mapping already exists for this IBAN."""
        account = await self._account_repo.find_by_id(mapping.accounting_account_id)
        if account is None:
            # This should never be raised. If it is, data integrity is broken!!!
            raise AccountNotFoundError(account_id=mapping.accounting_account_id)

        return ExternalAccountResult(
            account=account,
            mapping=mapping,
            transactions_reconciled=0,
            already_existed=True,
        )

    async def _handle_existing_account(
        self,
        account: Account,
        name: str,
        reconcile: bool,
        account_type: AccountType,
    ) -> ExternalAccountResult:
        """Handle case where an account exists but no mapping."""
        if account.iban is None:
            raise ValidationError(
                "Existing account %s has no IBAN, cannot create mapping" % account.id
            )

        if account.account_type != account_type:
            existing_acc_type = account.account_type.value
            requested_acc_type = account_type.value
            raise ValidationError(
                "Found existing account for IBAN %s but it is %s, not %s"
                % (account.iban, existing_acc_type, requested_acc_type)
            )
        mapping = AccountMapping(
            iban=account.iban,
            accounting_account_id=account.id,
            account_name=name,
            user_id=self._current_user.user_id,
            is_active=True,
        )
        await self._mapping_repo.save(mapping)

        reconciled_count = 0
        if reconcile:
            reconciled_count = await self._reconcile_transactions(
                iban=account.iban,
                account=account,
                account_type=account.account_type,
            )

        logger.info(
            "Created mapping for existing account: %s -> %s (reconciled %d)",
            mapping.iban,
            account.id,
            reconciled_count,
        )
        return ExternalAccountResult(
            account=account,
            mapping=mapping,
            transactions_reconciled=reconciled_count,
            already_existed=True,
        )

    async def _handle_new_account(
        self,
        iban: str,
        name: str,
        currency: Currency,
        account_type: AccountType,
        reconcile: bool,
    ) -> ExternalAccountResult:
        """Handle case where nothing exists — create both account and mapping."""
        account_number = self.generate_account_number(iban, account_type)

        account = Account(
            name=name,
            account_type=account_type,
            account_number=account_number,
            user_id=self._current_user.user_id,
            iban=iban,
            default_currency=currency,
        )
        await self._account_repo.save(account)

        mapping = AccountMapping(
            iban=iban,
            accounting_account_id=account.id,
            account_name=name,
            user_id=self._current_user.user_id,
            is_active=True,
        )
        await self._mapping_repo.save(mapping)

        reconciled_count = 0
        if reconcile:
            reconciled_count = await self._reconcile_transactions(
                iban=iban,
                account=account,
                account_type=account_type,
            )

        logger.info(
            "Created new external account: %s -> %s (reconciled %d)",
            iban,
            account.id,
            reconciled_count,
        )
        return ExternalAccountResult(
            account=account,
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
        """Delegate reconciliation to TransferReconciliationService."""
        reconciliation_service = TransferReconciliationService(self._transaction_repo)

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
