"""Create an external account and IBAN mapping for non-FinTS institutions."""

from __future__ import annotations

from typing import TYPE_CHECKING

from swen.application.integration.dtos import (
    AccountMappingDTO,
    CreateExternalAccountDTO,
    ExternalAccountCreatedDTO,
)
from swen.application.ports.unit_of_work import UnitOfWork
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
        uow: UnitOfWork,
    ):
        self._management_service = external_account_management_service
        self._uow = uow

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
            uow=factory.unit_of_work(),
        )

    async def execute(self, dto: CreateExternalAccountDTO) -> ExternalAccountCreatedDTO:
        """Execute the command.

        Validates inputs, delegates to the domain service, and maps
        the result to a DTO.

        Returns
        -------
            ExternalAccountCreatedDTO with the result.
        """
        async with self._uow:
            # Delegate to domain service
            result = await self._management_service.create_or_find_external_account(
                iban=dto.iban,
                name=dto.name,
                currency=dto.currency,
                account_type=dto.account_type,
                reconcile=dto.reconcile,
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
                created_at=result.mapping.created_at,
            ),
            transactions_reconciled=result.transactions_reconciled,
            already_existed=result.already_existed,
        )
