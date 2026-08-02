import logging

from fastapi import APIRouter

from swen.application.accounting.queries import (
    ListAccountsQuery,
)
from swen.application.integration.commands import RenameBankAccountCommand
from swen.presentation.api.accounting.schemas.accounts import (
    BankAccountListResponse,
    BankAccountRenameRequest,
    BankAccountResponse,
)
from swen.presentation.api.dependencies import RepoFactoryDep

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="List bank accounts",
    responses={
        200: {"description": "List of bank accounts with mappings"},
    },
)
async def list_bank_accounts(factory: RepoFactoryDep) -> BankAccountListResponse:
    """
    List all imported bank accounts with their mapping information.

    These are accounts that have been imported from bank connections.
    """
    query = ListAccountsQuery.from_factory(factory)
    dtos = await query.list_bank_accounts()

    return BankAccountListResponse(
        accounts=[BankAccountResponse.model_validate(dto) for dto in dtos],
    )


@router.patch(
    "/{iban}/rename",
    summary="Rename bank account",
    responses={
        200: {"description": "Bank account renamed"},
        404: {"description": "Bank account not found"},
    },
)
async def rename_bank_account(
    iban: str,
    request: BankAccountRenameRequest,
    factory: RepoFactoryDep,
) -> BankAccountResponse:
    """
    Rename an imported bank account.

    Updates both the accounting account name and the account mapping.
    """
    rename_bank_account_command = RenameBankAccountCommand.from_factory(factory)
    dto = await rename_bank_account_command.execute(
        iban=iban,
        new_name=request.name,
    )

    logger.info("Bank account renamed: %s -> %s", iban, request.name)

    return BankAccountResponse.model_validate(dto)
