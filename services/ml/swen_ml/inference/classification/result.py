"""Classification result structures."""

from dataclasses import dataclass
from uuid import UUID


@dataclass
class ClassificationResult:
    """Final output from classification pipeline."""

    transaction_id: UUID
    account_id: UUID | None  # None = unresolved, backend decides fallback
    account_number: str | None
    confidence: float
    resolved_by: str | None  # "example" | "anchor" | None
