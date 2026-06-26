"""Reclassification DTOs and progress events."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from swen.application.events.base import (
    SyncEventType,
    SyncProgressEvent,
)


class ReclassifyStartedEvent(SyncProgressEvent):
    """Emitted when reclassification begins."""

    model_config = ConfigDict(frozen=True)

    total: int = 0
    event_type: SyncEventType = Field(
        default=SyncEventType.RECLASSIFY_STARTED, init=False
    )


class ReclassifyProgressEvent(SyncProgressEvent):
    """Emitted after each ML classification chunk completes."""

    model_config = ConfigDict(frozen=True)

    current: int = 0
    total: int = 0
    event_type: SyncEventType = Field(
        default=SyncEventType.RECLASSIFY_PROGRESS, init=False
    )


class ReclassifyTransactionEvent(SyncProgressEvent):
    """Emitted when a single transaction is reclassified."""

    model_config = ConfigDict(frozen=True)

    transaction_id: UUID | None = None
    description: str = ""
    old_account: str = ""
    new_account: str = ""
    confidence: float = 0.0
    current: int = 0
    total: int = 0
    event_type: SyncEventType = Field(
        default=SyncEventType.RECLASSIFY_TRANSACTION, init=False
    )


class ReclassifyCompletedEvent(SyncProgressEvent):
    """Emitted when reclassification completes."""

    model_config = ConfigDict(frozen=True)

    total: int = 0
    reclassified: int = 0
    unchanged: int = 0
    failed: int = 0
    event_type: SyncEventType = Field(
        default=SyncEventType.RECLASSIFY_COMPLETED, init=False
    )


class ReclassifyFailedEvent(SyncProgressEvent):
    """Emitted when reclassification fails."""

    model_config = ConfigDict(frozen=True)

    error: str = ""
    event_type: SyncEventType = Field(
        default=SyncEventType.RECLASSIFY_FAILED, init=False
    )


class ReclassifiedTransactionDetail(BaseModel):
    """Detail of a single reclassified transaction."""

    model_config = ConfigDict(frozen=True)

    transaction_id: UUID
    old_account_number: str
    old_account_name: str
    new_account_number: str
    new_account_name: str
    confidence: float


class ReclassifyResultDTO(BaseModel):
    """Final result of a reclassification run."""

    model_config = ConfigDict(frozen=True)

    total_drafts: int
    reclassified_count: int
    unchanged_count: int
    failed_count: int
    details: tuple[ReclassifiedTransactionDetail, ...] = ()
