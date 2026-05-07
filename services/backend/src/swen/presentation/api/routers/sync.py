"""Sync router for bank transaction synchronization endpoints."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from swen.application.commands.integration.sync_bank_accounts_command import (
    SyncBankAccountsCommand,
)
from swen.application.dtos.integration import (
    BatchSyncResult,
    SyncProgressEvent,
)
from swen.application.queries import SyncRecommendationQuery, SyncStatusQuery
from swen.domain.shared.exceptions import DomainException, ErrorCode
from swen.infrastructure.event_publisher import SseSyncEventPublisher
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

    Returns a Server-Sent Events (SSE) stream with progress events.

    ## Event Types

    - **batch_sync_started**: Sync process beginning (includes `total_accounts`)
    - **batch_sync_completed**: All accounts synced (includes final totals)
    - **batch_sync_failed**: Entire batch sync failed (`code`, `error_key`)
    - **account_sync_started**: Starting to sync a specific account
    - **account_sync_fetched**: Transactions fetched from bank
    - **account_sync_completed**: Account sync finished
    - **account_sync_failed**: Account sync failed (`code`, `error_key`)
    - **classification_started**: ML batch classification beginning
    - **classification_progress**: ML classification progress update
    - **classification_completed**: ML batch classification finished
    - **transaction_classified**: Individual transaction classified and imported

    ## Terminal Payload

    After `batch_sync_completed`, a final `result` event is emitted with a
    reduced summary payload:

    ```
    event: result
    data: {"success": true, "total_imported": N, "total_skipped": N,
           "total_failed": N, "accounts_synced": N}
    ```

    ## SSE Format

    Each event is sent as:
    ```
    event: <event_type>
    data: {...}

    ```

    ## Example Usage (JavaScript)

    ```javascript
    const eventSource = new EventSource('/api/v1/sync/run/stream');
    eventSource.addEventListener('batch_sync_completed', (event) => {
      const data = JSON.parse(event.data);
      console.log('Done!', data.total_imported, 'imported');
    });
    eventSource.addEventListener('result', (event) => {
      const data = JSON.parse(event.data);
      eventSource.close();
    });
    ```
    """
    days = request.days if request else None
    iban = request.iban if request else None
    blz = request.blz if request else None
    auto_post = request.auto_post if request else None

    async def event_generator():
        """Generate SSE events from sync progress."""
        publisher = SseSyncEventPublisher()

        try:
            command = await SyncBankAccountsCommand.from_factory(
                factory, ml_client=ml_client, publisher=publisher
            )
        except DomainException as e:
            logger.exception("Failed to create sync command: %s", e)
            yield _format_sse_event(
                "batch_sync_failed",
                {"code": e.code.value, "error_key": "internal_error"},
            )
            return
        except Exception as e:
            logger.exception("Failed to create sync command: %s", e)
            yield _format_sse_event(
                "batch_sync_failed",
                {"code": ErrorCode.INTERNAL_ERROR.value, "error_key": "internal_error"},
            )
            return

        task = asyncio.create_task(
            command.execute(days=days, iban=iban, blz=blz, auto_post=auto_post)
        )

        try:
            async for item in publisher.events():
                if isinstance(item, SyncProgressEvent):
                    yield _format_sse_event(item.event_type.value, item.to_dict())
                elif isinstance(item, BatchSyncResult):
                    # Terminal result payload from publish_terminal
                    final_data = {
                        "success": item.success,
                        "total_imported": item.total_imported,
                        "total_skipped": item.total_skipped,
                        "total_failed": item.total_failed,
                        "accounts_synced": item.accounts_synced,
                    }
                    yield _format_sse_event("result", final_data)

            # Surface any exception raised by the orchestration task
            await task

        except DomainException as e:
            task.cancel()
            logger.warning("Streaming sync failed (domain): %s", e)
            yield _format_sse_event(
                "batch_sync_failed",
                {"code": e.code.value, "error_key": "internal_error"},
            )
        except Exception as e:
            task.cancel()
            logger.exception("Streaming sync failed (unexpected): %s", e)
            yield _format_sse_event(
                "batch_sync_failed",
                {"code": ErrorCode.INTERNAL_ERROR.value, "error_key": "internal_error"},
            )
        finally:
            await publisher.close()
            if not task.done():
                task.cancel()

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
