"""Transactions router for transaction management endpoints."""

import logging
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from swen.application.commands.accounting import (
    CreateSimpleTransactionCommand,
    CreateTransactionCommand,
    DeleteTransactionCommand,
    EditTransactionCommand,
    PostTransactionCommand,
    UnpostTransactionCommand,
)
from swen.application.queries import ListTransactionsQuery
from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.value_objects import JournalEntryInput
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.transactions import (
    JournalEntryResponse,
    TransactionCreateRequest,
    TransactionCreateSimpleRequest,
    TransactionListItemResponse,
    TransactionListResponse,
    TransactionResponse,
    TransactionUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Type aliases for query parameters using Annotated (modern FastAPI pattern)
# Note: Don't set default in Query() when using Annotated - set it with = instead
DaysFilter = Annotated[
    int,
    Query(ge=1, le=365, description="Days to look back"),
]
LimitFilter = Annotated[
    int,
    Query(ge=1, le=500, description="Max transactions"),
]
StatusFilter = Annotated[
    str | None,
    Query(description="Filter by status: 'posted' or 'draft'"),
]
AccountNumberFilter = Annotated[
    str | None,
    Query(description="Filter by account number"),
]
ExcludeTransfersFilter = Annotated[
    bool | None,
    Query(description="Exclude internal transfers (default: auto)"),
]
ForceDeleteFilter = Annotated[
    bool,
    Query(description="Force deletion even if posted (will unpost first)"),
]


def _transaction_to_response(txn: Transaction) -> TransactionResponse:
    """Convert domain Transaction to response schema."""
    entries = [
        JournalEntryResponse(
            account_id=entry.account.id,
            account_name=entry.account.name,
            account_type=entry.account.account_type.value,
            # Use is_debit()/is_credit() to check for positive amounts
            # (entry.debit is always a Money object, never None)
            debit=entry.debit.amount if entry.is_debit() else None,
            credit=entry.credit.amount if entry.is_credit() else None,
            currency=(
                entry.debit.currency.code
                if entry.is_debit()
                else entry.credit.currency.code
            ),
        )
        for entry in txn.entries
    ]

    return TransactionResponse(
        id=txn.id,
        date=txn.date,
        description=txn.description,
        counterparty=txn.counterparty,
        counterparty_iban=txn.counterparty_iban,
        source=txn.source.value,
        source_iban=txn.source_iban,
        is_posted=txn.is_posted,
        is_internal_transfer=txn.is_internal_transfer,
        created_at=txn.created_at,
        entries=entries,
        metadata=txn.metadata_raw or {},
    )


def _list_item_to_response(dto) -> TransactionListItemResponse:
    """Convert DTO to response schema."""
    return TransactionListItemResponse(
        id=dto.id,
        short_id=dto.short_id,
        date=dto.date,
        description=dto.description,
        counterparty=dto.counterparty,
        counter_account=dto.counter_account,
        debit_account=dto.debit_account,
        credit_account=dto.credit_account,
        amount=dto.amount,
        currency=dto.currency,
        is_income=dto.is_income,
        is_posted=dto.is_posted,
        is_internal_transfer=dto.is_internal_transfer,
    )


@router.get(
    "",
    summary="List transactions",
    responses={
        200: {"description": "List of transactions"},
    },
)
async def list_transactions(  # NOQA: PLR0913
    factory: RepoFactory,
    days: DaysFilter = 30,
    limit: LimitFilter = 50,
    status_filter: StatusFilter = None,
    account_number: AccountNumberFilter = None,
    exclude_transfers: ExcludeTransfersFilter = None,
) -> TransactionListResponse:
    """
    List transactions for the current user.

    Supports filtering by:
    - Date range (days back from today)
    - Status (posted/draft)
    - Account number
    - Internal transfers (excluded by default when not filtering by account)
    """
    query = ListTransactionsQuery(
        transaction_repository=factory.transaction_repository(),
        account_repository=factory.account_repository(),
    )

    # Use query's execute method for counts
    result = await query.execute(
        days=days,
        limit=limit,
        status_filter=status_filter,
        iban_filter=account_number,
        exclude_transfers=exclude_transfers,
    )

    # Use query's DTO method for formatted list items
    dto_result = await query.get_transaction_list(
        days=days,
        limit=limit,
        status_filter=status_filter,
        iban_filter=account_number,
        exclude_transfers=exclude_transfers,
    )

    return TransactionListResponse(
        transactions=[_list_item_to_response(dto) for dto in dto_result.transactions],
        total=result.total_count,
        draft_count=result.draft_count,
        posted_count=result.posted_count,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual transaction",
    responses={
        201: {"description": "Transaction created successfully"},
        400: {"description": "Invalid entries or accounts not found"},
        422: {"description": "Validation error (entries don't balance)"},
    },
)
async def create_transaction(
    request: TransactionCreateRequest,
    factory: RepoFactory,
) -> TransactionResponse:
    """
    Create a manual transaction with explicit journal entries.

    This endpoint creates a transaction following double-entry bookkeeping rules:
    - At least 2 journal entries required
    - Total debits must equal total credits
    - **Supports multi-entry transactions** (e.g., split purchases across categories)

    **Example expense (groceries €45.99):**
    ```json
    {
      "date": "2024-12-05T14:30:00Z",
      "description": "REWE Supermarket",
      "entries": [
        {"account_id": "<expense-account-id>", "debit": "45.99", "credit": "0"},
        {"account_id": "<asset-account-id>", "debit": "0", "credit": "45.99"}
      ],
      "auto_post": true
    }
    ```

    **Example split expense (groceries €30 + household €20):**
    ```json
    {
      "date": "2024-12-05T14:30:00Z",
      "description": "REWE Mixed Purchase",
      "entries": [
        {"account_id": "<groceries-id>", "debit": "30.00", "credit": "0"},
        {"account_id": "<household-id>", "debit": "20.00", "credit": "0"},
        {"account_id": "<checking-id>", "debit": "0", "credit": "50.00"}
      ],
      "auto_post": true
    }
    ```
    """
    # Validate entries balance
    total_debit = sum((e.debit for e in request.entries), start=Decimal("0"))
    total_credit = sum((e.credit for e in request.entries), start=Decimal("0"))

    if total_debit != total_credit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Entries don't balance: debits={total_debit}, credits={total_credit}"
            ),
        )

    if total_debit == Decimal("0"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Transaction must have non-zero amounts",
        )

    # Convert request entries to domain JournalEntryInput objects
    # Each entry in the request can have either debit or credit (or both if split)
    entry_inputs = _convert_to_entry_inputs(request.entries)

    command = CreateTransactionCommand.from_factory(factory)

    try:
        txn = await command.execute(
            description=request.description,
            entries=entry_inputs,
            counterparty=request.counterparty,
            date=request.date,
            is_manual_entry=True,
            auto_post=request.auto_post,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Manual transaction created: %s", txn.id)
    return _transaction_to_response(txn)


def _convert_to_entry_inputs(entries: list) -> list[JournalEntryInput]:
    """Convert API entry requests to domain JournalEntryInput objects.

    Each API entry can have both debit and credit fields (for flexibility),
    but the domain requires exactly one per entry. We split entries that
    have both into two separate JournalEntryInput objects.

    Parameters
    ----------
    entries
        List of JournalEntryRequest from the API

    Returns
    -------
    List of JournalEntryInput domain value objects
    """
    result = []
    for entry in entries:
        if entry.debit > 0:
            result.append(JournalEntryInput.debit_entry(entry.account_id, entry.debit))
        if entry.credit > 0:
            result.append(
                JournalEntryInput.credit_entry(entry.account_id, entry.credit),
            )
    return result


@router.post(
    "/simple",
    status_code=status.HTTP_201_CREATED,
    summary="Create a simple transaction (auto-resolves accounts)",
    responses={
        201: {"description": "Transaction created successfully"},
        400: {"description": "Accounts not found or cannot be resolved"},
    },
)
async def create_simple_transaction(
    request: TransactionCreateSimpleRequest,
    factory: RepoFactory,
) -> TransactionResponse:
    """
    Create a transaction with automatic account resolution.

    This is the simplified endpoint - just specify the amount and let the
    system figure out the double-entry details:

    - **Negative amount** = expense (e.g., `-45.99` for groceries)
    - **Positive amount** = income (e.g., `3000.00` for salary)

    The system automatically:
    - Finds your default asset account (checking/savings)
    - Selects an appropriate expense or income category
    - Creates the balanced journal entries

    **Example expense:**
    ```json
    {
      "date": "2024-12-05T14:30:00Z",
      "description": "REWE Supermarket",
      "amount": "-45.99",
      "counterparty": "REWE",
      "auto_post": true
    }
    ```

    **Example income:**
    ```json
    {
      "date": "2024-12-01T09:00:00Z",
      "description": "Salary December",
      "amount": "3500.00",
      "counterparty": "ACME Corp",
      "auto_post": true
    }
    ```
    """
    command = CreateSimpleTransactionCommand.from_factory(factory)

    try:
        txn = await command.execute(
            description=request.description,
            amount=request.amount,
            asset_account_hint=request.asset_account,
            category_account_hint=request.category_account,
            counterparty=request.counterparty,
            date=request.date,
            auto_post=request.auto_post,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Simple transaction created: %s", txn.id)
    return _transaction_to_response(txn)


@router.get(
    "/{transaction_id}",
    summary="Get transaction details",
    responses={
        200: {"description": "Transaction details"},
        404: {"description": "Transaction not found"},
    },
)
async def get_transaction(
    transaction_id: UUID,
    factory: RepoFactory,
) -> TransactionResponse:
    """Get detailed information about a specific transaction."""
    query = ListTransactionsQuery(
        transaction_repository=factory.transaction_repository(),
        account_repository=factory.account_repository(),
    )

    txn = await query.find_by_id(transaction_id)
    if txn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    return _transaction_to_response(txn)


@router.put(
    "/{transaction_id}",
    summary="Update a transaction",
    responses={
        200: {"description": "Transaction updated"},
        400: {"description": "Invalid update request"},
        404: {"description": "Transaction not found"},
        422: {"description": "Entries don't balance or other validation error"},
    },
)
async def update_transaction(
    transaction_id: UUID,
    request: TransactionUpdateRequest,
    factory: RepoFactory,
) -> TransactionResponse:
    """
    Update an existing transaction.

    You can update:
    - **description**: Change the transaction description
    - **counterparty**: Change the merchant/payer name
    - **category_account_id**: Re-categorize to a different expense/income account
    - **entries**: Replace all journal entries (for splitting, amount changes, etc.)

    Note: `entries` and `category_account_id` are mutually exclusive.

    If the transaction is posted and `repost=True` (default), it will be
    automatically unposted, modified, and re-posted.
    """
    # Convert entries from request schema to domain value objects
    entry_inputs = None
    if request.entries is not None:
        entry_inputs = _convert_to_entry_inputs(request.entries)

    command = EditTransactionCommand.from_factory(factory)

    try:
        txn = await command.execute(
            transaction_id=transaction_id,
            entries=entry_inputs,
            description=request.description,
            counterparty=request.counterparty,
            category_account_id=request.category_account_id,
            repost=request.repost,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Transaction updated: %s", transaction_id)
    return _transaction_to_response(txn)


@router.post(
    "/{transaction_id}/post",
    summary="Post a transaction",
    responses={
        200: {"description": "Transaction posted"},
        400: {"description": "Transaction already posted"},
        404: {"description": "Transaction not found"},
    },
)
async def post_transaction(
    transaction_id: UUID,
    factory: RepoFactory,
) -> TransactionResponse:
    """
    Post a draft transaction.

    Posting a transaction makes it permanent and affects account balances.
    """
    command = PostTransactionCommand.from_factory(factory)

    try:
        txn = await command.execute(transaction_id=transaction_id)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Transaction posted: %s", transaction_id)
    return _transaction_to_response(txn)


@router.post(
    "/{transaction_id}/unpost",
    summary="Unpost a transaction",
    responses={
        200: {"description": "Transaction unposted"},
        400: {"description": "Transaction not posted"},
        404: {"description": "Transaction not found"},
    },
)
async def unpost_transaction(
    transaction_id: UUID,
    factory: RepoFactory,
) -> TransactionResponse:
    """
    Unpost a transaction (revert to draft).

    This removes the transaction's effect on account balances.
    """
    command = UnpostTransactionCommand.from_factory(factory)

    try:
        txn = await command.execute(transaction_id=transaction_id)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Transaction unposted: %s", transaction_id)
    return _transaction_to_response(txn)


@router.delete(
    "/{transaction_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a transaction",
    responses={
        204: {"description": "Transaction deleted"},
        400: {"description": "Transaction is posted (must unpost first or use force)"},
        404: {"description": "Transaction not found"},
    },
)
async def delete_transaction(
    transaction_id: UUID,
    factory: RepoFactory,
    force: ForceDeleteFilter = False,
) -> None:
    """
    Delete a transaction permanently.

    By default, only draft transactions can be deleted. Posted transactions
    must be unposted first, or use `force=true` to automatically unpost
    before deletion.

    **Warning**: This action is permanent and cannot be undone.
    """
    command = DeleteTransactionCommand.from_factory(factory)

    try:
        await command.execute(transaction_id=transaction_id, force=force)
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info("Transaction deleted: %s", transaction_id)
