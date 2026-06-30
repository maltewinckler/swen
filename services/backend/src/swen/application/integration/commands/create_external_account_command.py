"""Create an external account and IBAN mapping for non-FinTS institutions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.integration.dtos import (
    AccountMappingDTO,
    ExternalAccountCreatedDTO,
)
from swen.domain.accounting.entities import AccountType
from swen.domain.integration.services import ExternalAccountManagementService

if TYPE_CHECKING:
    from swen.application.factories import RepositoryFactory
    from swen.domain.integration.services.external_account_management_service import (
        ExternalAccountResult,
    )


class CreateExternalAccountCommand:
    """Command to create or find an external account mapping.

    This command is a thin orchestrator that validates inputs, delegates
    business logic to ExternalAccountManagementService, and maps results
    to DTOs.
    """

    def __init__(
        self,
        external_account_management_service: ExternalAccountManagementService,
    ):
        self._management_service = external_account_management_service

    @classmethod
    def from_factory(
        cls,
        factory: RepositoryFactory,
    ) -> CreateExternalAccountCommand:
        return cls(
            external_account_management_service=ExternalAccountManagementService(
                account_repository=factory.account_repository(),
                mapping_repository=factory.account_mapping_repository(),
                transaction_repository=factory.transaction_repository(),
                current_user=factory.current_user,
            ),
        )

    async def execute(
        self,
        iban: str,
        name: str,
        currency: str = "EUR",
        account_type: AccountType = AccountType.ASSET,
        reconcile: bool = True,
    ) -> ExternalAccountCreatedDTO:
        """Execute the command.

        Validates inputs, delegates to the domain service, and maps
        the result to a DTO.

        Returns
        -------
            ExternalAccountCreatedDTO with the result.
        """
        # Delegate to domain service
        result = await self._management_service.create_or_find_external_account(
            iban=iban,
            name=name,
            currency=currency,
            account_type=account_type,
            reconcile=reconcile,
        )

        # Map to DTO
        return self._build_dto(result)

    def _build_dto(self, result: ExternalAccountResult) -> ExternalAccountCreatedDTO:
        """Map domain result to application DTO."""
        return ExternalAccountCreatedDTO(
            mapping=AccountMappingDTO(
                id=result.mapping.id,
                iban=result.mapping.iban,
                account_name=result.mapping.account_name,
                accounting_account_id=result.mapping.accounting_account_id,
                accounting_account_name=result.account.name,
                accounting_account_number=result.account.account_number,
                created_at=result.mapping.created_at.isoformat()
                if result.mapping.created_at
                else None,
            ),
            transactions_reconciled=result.transactions_reconciled,
            already_existed=result.already_existed,
        )
