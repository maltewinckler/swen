"""ML batch classification progress events."""

from __future__ import annotations

from typing import Optional

from pydantic import ConfigDict, Field

from swen.application.events.base import SyncEventType, SyncProgressEvent


class ClassificationStartedEvent(SyncProgressEvent):
    """Emitted when ML batch classification begins."""

    model_config = ConfigDict(frozen=True)

    event_type: SyncEventType = Field(
        default=SyncEventType.CLASSIFICATION_STARTED, init=False
    )
    iban: str = ""


class ClassificationProgressEvent(SyncProgressEvent):
    """Emitted during ML batch classification for progress updates."""

    model_config = ConfigDict(frozen=True)

    event_type: SyncEventType = Field(
        default=SyncEventType.CLASSIFICATION_PROGRESS, init=False
    )
    iban: str = ""
    current: int = 0
    total: int = 0
    last_merchant: Optional[str] = None


class ClassificationCompletedEvent(SyncProgressEvent):
    """Emitted when ML batch classification completes."""

    model_config = ConfigDict(frozen=True)

    event_type: SyncEventType = Field(
        default=SyncEventType.CLASSIFICATION_COMPLETED, init=False
    )
    iban: str = ""
    total: int = 0
    recurring_detected: int = 0
    merchants_extracted: int = 0
    processing_time_ms: int = 0
