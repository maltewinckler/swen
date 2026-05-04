"""Sync router for bank transaction synchronization endpoints."""

import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from swen.application.commands import BatchSyncCommand
from swen.application.dtos.integration import SyncProgressEvent
from swen.application.queries import SyncRecommendationQuery, SyncStatusQuery
from swen.domain.shared.exceptions import DomainException, ErrorCode
from swen.presentation.api.dependencies import MLClient, RepoFactory
from swen.presentation.api.schemas.sync import (
    AccountSyncRecommendationResponse,
    SyncRecommendationResponse,
    SyncRunRequest,
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
         - Call `POST /sync/run/stream` with `days` parameter
    3. Otherwise:
         - Call `POST /sync/run/stream` without `days` (adaptive mode)
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
    ml_client: MLClient,
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

    The final `result` event is a reduced summary payload containing only
    `success`, `total_imported`, `total_skipped`, `total_failed`, and
    `accounts_synced`.
    """
    days = request.days if request else None
    iban = request.iban if request else None
    blz = request.blz if request else None
    auto_post = request.auto_post if request else None

    async def event_generator():
        """Generate SSE events from sync progress."""
        try:
            command = await BatchSyncCommand.from_factory(factory, ml_client=ml_client)
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
                # Keep the SSE terminal payload intentionally small and aligned
                # with the frontend summary UI.
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
