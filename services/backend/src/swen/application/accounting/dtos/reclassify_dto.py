"""Reclassification DTOs and progress events."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from swen.application.events.base import (
    SyncEventType,
    SyncProgressEvent,
)

# ═══════════════════════════════════════════════════════════════
#              Reclassification progress events (SSE)
# ═══════════════════════════════════════════════════════════════


@dataclass
class ReclassifyStartedEvent(SyncProgressEvent):
    """Emitted when reclassification begins."""

    total: int = 0

    def __init__(self, total: int, message: str | None = None):  # noqa: ARG002
        super().__init__(
            event_type=SyncEventType.RECLASSIFY_STARTED,
        )
        self.total = total

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["total"] = self.total
        return d


@dataclass
class ReclassifyProgressEvent(SyncProgressEvent):
    """Emitted after each ML classification chunk completes."""

    current: int = 0
    total: int = 0

    def __init__(
        self,
        current: int,
        total: int,
        message: str | None = None,  # noqa: ARG002
    ):
        super().__init__(
            event_type=SyncEventType.RECLASSIFY_PROGRESS,
        )
        self.current = current
        self.total = total

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["current"] = self.current
        d["total"] = self.total
        return d


@dataclass
class ReclassifyTransactionEvent(SyncProgressEvent):
    """Emitted when a single transaction is reclassified."""

    transaction_id: UUID | None = None
    description: str = ""
    old_account: str = ""
    new_account: str = ""
    confidence: float = 0.0
    current: int = 0
    total: int = 0

    def __init__(  # noqa: PLR0913
        self,
        transaction_id: UUID,
        description: str,
        old_account: str,
        new_account: str,
        confidence: float,
        current: int,
        total: int,
        message: str | None = None,  # noqa: ARG002
    ):
        super().__init__(
            event_type=SyncEventType.RECLASSIFY_TRANSACTION,
        )
        self.transaction_id = transaction_id
        self.description = description
        self.old_account = old_account
        self.new_account = new_account
        self.confidence = confidence
        self.current = current
        self.total = total

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["transaction_id"] = str(self.transaction_id)
        d["description"] = self.description
        d["old_account"] = self.old_account
        d["new_account"] = self.new_account
        d["confidence"] = self.confidence
        d["current"] = self.current
        d["total"] = self.total
        return d


@dataclass
class ReclassifyCompletedEvent(SyncProgressEvent):
    """Emitted when reclassification completes."""

    total: int = 0
    reclassified: int = 0
    unchanged: int = 0
    failed: int = 0

    def __init__(
        self,
        total: int,
        reclassified: int,
        unchanged: int,
        failed: int,
        message: str | None = None,  # noqa: ARG002
    ):
        super().__init__(
            event_type=SyncEventType.RECLASSIFY_COMPLETED,
        )
        self.total = total
        self.reclassified = reclassified
        self.unchanged = unchanged
        self.failed = failed

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["total"] = self.total
        d["reclassified"] = self.reclassified
        d["unchanged"] = self.unchanged
        d["failed"] = self.failed
        return d


@dataclass
class ReclassifyFailedEvent(SyncProgressEvent):
    """Emitted when reclassification fails."""

    error: str = ""

    def __init__(self, error: str, message: str | None = None):  # noqa: ARG002
        super().__init__(
            event_type=SyncEventType.RECLASSIFY_FAILED,
        )
        self.error = error

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["error"] = self.error
        return d


# ═══════════════════════════════════════════════════════════════
#              Result DTO (final summary)
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class ReclassifiedTransactionDetail:
    """Detail of a single reclassified transaction."""

    transaction_id: UUID
    old_account_number: str
    old_account_name: str
    new_account_number: str
    new_account_name: str
    confidence: float


@dataclass(frozen=True)
class ReclassifyResultDTO:
    """Final result of a reclassification run."""

    total_drafts: int
    reclassified_count: int
    unchanged_count: int
    failed_count: int
    details: tuple[ReclassifiedTransactionDetail, ...] = field(default_factory=tuple)
