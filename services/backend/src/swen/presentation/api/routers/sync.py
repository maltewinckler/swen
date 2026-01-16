"""Sync router for bank transaction synchronization endpoints."""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from swen.application.commands import BatchSyncCommand
from swen.application.dtos.integration import SyncProgressEvent
from swen.application.queries import SyncRecommendationQuery, SyncStatusQuery
from swen.domain.shared.exceptions import DomainException, ErrorCode
from swen.presentation.api.dependencies import RepoFactory
from swen.presentation.api.schemas.sync import (
    AccountSyncRecommendationResponse,
    AccountSyncStatsResponse,
    OpeningBalanceResponse,
    SyncRecommendationResponse,
    SyncRunRequest,
    SyncRunResponse,
    SyncStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/recommendation",
    summary="Get sync recommendations",
    responses={
        200: {"description": "Sync recommendations for adaptive sync"},
    },
)
async def get_sync_recommendation(
    factory: RepoFactory,
) -> SyncRecommendationResponse:
    """
    Get sync recommendations for adaptive synchronization.

    Returns per-account information to help implement adaptive sync:

    - **First sync accounts**: Accounts that have never been synced. The frontend
      should prompt the user to specify how many days of history to load.
    - **Subsequent sync accounts**: Accounts with sync history. Use adaptive mode
      (no `days` parameter) to automatically sync from last sync date.

    ## Recommended Flow

    1. Call `GET /sync/recommendation`
    2. If `has_first_sync_accounts` is true:
       - Show a dialog asking user how many days to load
       - Call `POST /sync/run` with `days` parameter
    3. Otherwise:
       - Call `POST /sync/run` without `days` (adaptive mode)
    """
    query = SyncRecommendationQuery.from_factory(factory)
    result = await query.execute()

    return SyncRecommendationResponse(
        accounts=[
            AccountSyncRecommendationResponse(
                iban=acc.iban,
                is_first_sync=acc.is_first_sync,
                recommended_start_date=acc.recommended_start_date,
                last_successful_sync_date=acc.last_successful_sync_date,
                successful_import_count=acc.successful_import_count,
            )
            for acc in result.accounts
        ],
        has_first_sync_accounts=result.has_first_sync_accounts,
        total_accounts=result.total_accounts,
    )


@router.post(
    "/run",
    summary="Run transaction sync",
    responses={
        200: {"description": "Sync completed successfully"},
        400: {"description": "Invalid parameters"},
        503: {"description": "Sync failed due to bank connection issues"},
        504: {"description": "TAN approval timeout (5 minutes)"},
    },
)
async def run_sync(
    factory: RepoFactory,
    request: Optional[SyncRunRequest] = None,
) -> SyncRunResponse:
    """
    Trigger bank transaction synchronization.

    Fetches recent transactions from all connected bank accounts and imports them
    into the accounting system. Automatically detects internal transfers between
    your own accounts and creates proper double-entry bookings.

    ## Adaptive Sync Mode

    When `days` is omitted or null, **adaptive sync** is used:
    - **First sync** (no history): Uses 90 days as default
    - **Subsequent syncs**: Syncs from last successful import date + 1 day

    For first-time syncs where you want to specify the number of days, use
    `GET /sync/recommendation` first to check which accounts need initial setup.

    ## TAN Handling

    For banks using **decoupled TAN** (e.g., SecureGo plus, pushTAN), the API will
    **block and wait** for you to approve the transaction in your banking app:

    - The request polls the bank every 5 seconds
    - Maximum wait time: **5 minutes** (then timeout)
    - You just need to open your banking app and approve when prompted

    **Important:** Set your HTTP client timeout to at least 6 minutes when using
    this endpoint with TAN-requiring operations (typically 180+ days of history).

    For banks requiring **interactive TAN** (photoTAN, chipTAN, SMS-TAN), use the
    CLI instead as user input is required.

    Request body is optional - adaptive sync will be used if not provided.
    """
    # Use adaptive mode (None) if no request body or no days specified
    days = request.days if request else None
    iban = request.iban if request else None
    blz = request.blz if request else None
    auto_post = request.auto_post if request else None

    # Create batch sync command (async factory due to account existence check)
    try:
        command = await BatchSyncCommand.from_factory(factory)
    except Exception as e:
        logger.exception("Failed to create sync command: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize sync command",
        ) from e

    try:
        result = await command.execute(
            days=days,
            iban=iban,
            blz=blz,
            auto_post=auto_post,
        )
        await factory.session.commit()
    except Exception:
        await factory.session.rollback()
        # Let the global exception handler process domain exceptions
        raise

    logger.info(
        "Sync completed: %d imported, %d skipped, %d failed",
        result.total_imported,
        result.total_skipped,
        result.total_failed,
    )

    # Convert DTO to response
    return SyncRunResponse(
        success=result.success,
        synced_at=result.synced_at,
        start_date=result.start_date,
        end_date=result.end_date,
        auto_post=result.auto_post,
        total_fetched=result.total_fetched,
        total_imported=result.total_imported,
        total_skipped=result.total_skipped,
        total_failed=result.total_failed,
        accounts_synced=result.accounts_synced,
        account_stats=[
            AccountSyncStatsResponse(
                iban=stats.iban,
                fetched=stats.fetched,
                imported=stats.imported,
                skipped=stats.skipped,
                failed=stats.failed,
            )
            for stats in result.account_stats
        ],
        opening_balances=[
            OpeningBalanceResponse(
                iban=ob.iban,
                amount=ob.amount,
            )
            for ob in result.opening_balances
        ],
        errors=result.errors,
        opening_balance_account_missing=result.opening_balance_account_missing,
    )


@router.post(
    "/run/stream",
    summary="Run transaction sync with streaming progress",
    responses={
        200: {
            "description": "SSE stream of sync progress events",
            "content": {"text/event-stream": {}},
        },
        400: {"description": "Invalid parameters"},
    },
)
async def run_sync_streaming(
    factory: RepoFactory,
    request: Optional[SyncRunRequest] = None,
) -> StreamingResponse:
    """
    Trigger bank transaction synchronization with real-time progress updates.

    Returns a Server-Sent Events (SSE) stream with progress events:

    ## Event Types

    - **sync_started**: Sync process beginning (includes total_accounts)
    - **account_started**: Starting to sync a specific account
    - **account_fetched**: Transactions fetched from bank
    - **account_classifying**: Classification progress (current/total)
    - **transaction_classified**: Individual transaction classified
    - **account_completed**: Account sync finished
    - **account_failed**: Account sync failed
    - **sync_completed**: All accounts synced (includes final totals)
    - **sync_failed**: Sync process failed

    ## SSE Format

    Each event is sent as:
    ```
    event: <event_type>
    data: {"message": "...", "iban": "...", ...}

    ```

    ## Example Usage (JavaScript)

    ```javascript
    const eventSource = new EventSource('/api/v1/sync/run/stream');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data.event_type, data.message);
    };
    eventSource.addEventListener('sync_completed', (event) => {
      const data = JSON.parse(event.data);
      console.log('Done!', data.total_imported, 'imported');
      eventSource.close();
    });
    ```

    The final event (sync_completed or sync_failed) also includes the full
    BatchSyncResult in the `result` field.
    """
    days = request.days if request else None
    iban = request.iban if request else None
    blz = request.blz if request else None
    auto_post = request.auto_post if request else None

    async def event_generator():
        """Generate SSE events from sync progress."""
        try:
            command = await BatchSyncCommand.from_factory(factory)
        except DomainException as e:
            logger.exception("Failed to create sync command: %s", e)
            yield _format_sse_event(
                "sync_failed",
                {"message": e.message, "code": e.code.value},
            )
            return
        except Exception as e:
            logger.exception("Failed to create sync command: %s", e)
            yield _format_sse_event(
                "sync_failed",
                {
                    "message": "Failed to initialize sync",
                    "code": ErrorCode.INTERNAL_ERROR.value,
                },
            )
            return

        result = None
        try:
            async for event in command.execute_streaming(
                days=days,
                iban=iban,
                blz=blz,
                auto_post=auto_post,
            ):
                if isinstance(event, SyncProgressEvent):
                    yield _format_sse_event(event.event_type.value, event.to_dict())
                else:
                    # This is the final result
                    result = event

            # Commit the transaction
            await factory.session.commit()

            # Send final result with the completed event data
            if result:
                logger.info(
                    "Streaming sync completed: %d imported, %d skipped, %d failed",
                    result.total_imported,
                    result.total_skipped,
                    result.total_failed,
                )
                # Include full result in the final event
                final_data = {
                    "success": result.success,
                    "total_imported": result.total_imported,
                    "total_skipped": result.total_skipped,
                    "total_failed": result.total_failed,
                    "accounts_synced": result.accounts_synced,
                }
                yield _format_sse_event("result", final_data)

        except DomainException as e:
            await factory.session.rollback()
            logger.warning("Streaming sync failed (domain): %s", e)
            yield _format_sse_event(
                "sync_failed",
                {"message": e.message, "code": e.code.value},
            )
        except Exception as e:
            await factory.session.rollback()
            logger.exception("Streaming sync failed (unexpected): %s", e)
            # Don't leak internal exception details to client
            yield _format_sse_event(
                "sync_failed",
                {
                    "message": "Sync failed unexpectedly",
                    "code": ErrorCode.INTERNAL_ERROR.value,
                },
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


def _format_sse_event(event_type: str, data: dict) -> str:
    """Format data as an SSE event string."""
    json_data = json.dumps(data)
    return f"event: {event_type}\ndata: {json_data}\n\n"


@router.get(
    "/status",
    summary="Get sync status",
    responses={
        200: {"description": "Sync status statistics"},
    },
)
async def get_sync_status(
    factory: RepoFactory,
) -> SyncStatusResponse:
    """
    Get transaction sync status and statistics.

    Returns import history statistics showing how many transactions have been:
    - Successfully imported
    - Failed
    - Pending
    - Skipped (duplicates)
    """
    query = SyncStatusQuery.from_factory(factory)
    result = await query.execute()

    return SyncStatusResponse(
        success_count=result.success_count,
        failed_count=result.failed_count,
        pending_count=result.pending_count,
        duplicate_count=result.duplicate_count,
        skipped_count=result.skipped_count,
        total_count=result.total_count,
    )
