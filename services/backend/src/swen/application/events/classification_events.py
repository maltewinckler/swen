"""ML batch classification progress events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from swen.application.events.base import SyncEventType, SyncProgressEvent


@dataclass
class ClassificationStartedEvent(SyncProgressEvent):
    """Emitted when ML batch classification begins."""

    event_type: SyncEventType = field(
        default=SyncEventType.CLASSIFICATION_STARTED, init=False
    )
    iban: str = ""


@dataclass
class ClassificationProgressEvent(SyncProgressEvent):
    """Emitted during ML batch classification for progress updates."""

    event_type: SyncEventType = field(
        default=SyncEventType.CLASSIFICATION_PROGRESS, init=False
    )
    iban: str = ""
    current: int = 0
    total: int = 0
    last_merchant: Optional[str] = None


@dataclass
class ClassificationCompletedEvent(SyncProgressEvent):
    """Emitted when ML batch classification completes."""

    event_type: SyncEventType = field(
        default=SyncEventType.CLASSIFICATION_COMPLETED, init=False
    )
    iban: str = ""
    total: int = 0
    recurring_detected: int = 0
    merchants_extracted: int = 0
    processing_time_ms: int = 0
