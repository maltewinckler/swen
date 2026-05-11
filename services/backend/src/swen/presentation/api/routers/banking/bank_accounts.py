import logging
from uuid import UUID

from fastapi import APIRouter

from swen.application.commands.integration import RenameBankAccountCommand
from swen.application.queries import (
    ListAccountsQuery,
)
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.accounts import (
    BankAccountListResponse,
    BankAccountRenameRequest,
    BankAccountResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    summary="List bank accounts",
    responses={
        200: {"description": "List of bank accounts with mappings"},
    },
)
async def list_bank_accounts(
    factory: RepoFactory,
) -> BankAccountListResponse:
    """
    List all imported bank accounts with their mapping information.

    These are accounts that have been imported from bank connections.
    """
    query = ListAccountsQuery.from_factory(factory)
    dtos = await query.list_bank_accounts()

    return BankAccountListResponse(
        accounts=[
            BankAccountResponse(
                id=UUID(dto.id),
                name=dto.name,
                account_number=dto.account_number,
                iban=dto.iban,
                currency=dto.currency,
                is_active=dto.is_active,
            )
            for dto in dtos
        ],
        total=len(dtos),
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
    factory: RepoFactory,
) -> BankAccountResponse:
    """
    Rename an imported bank account.

    Updates both the accounting account name and the account mapping.
    """
    import_service = RenameBankAccountCommand.from_factory(factory)

    # Normalize IBAN (presentation concern - input sanitization)
    normalized_iban = iban.replace(" ", "").upper()

    try:
        dto = await import_service.execute(
            iban=normalized_iban,
            new_name=request.name,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Bank account renamed: %s -> %s", normalized_iban, request.name)

    return BankAccountResponse(
        id=UUID(dto.id),
        name=dto.name,
        account_number=dto.account_number,
        iban=dto.iban,
        currency=dto.currency,
        is_active=dto.is_active,
    )
