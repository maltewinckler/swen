"""Typed metadata for accounting transactions."""

from datetime import datetime
from typing import Annotated, Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from swen.domain.accounting.value_objects.transaction_source import TransactionSource
from swen.domain.shared.iban import normalize_iban


class AIResolutionMetadata(BaseModel):
    """AI counter-account resolution metadata."""

    model_config = ConfigDict(frozen=True)

    # What AI suggested
    suggested_counter_account_id: str = Field(
        description="UUID of the account AI suggested",
    )
    suggested_counter_account_name: Optional[str] = Field(
        default=None,
        description="Name of suggested account (if accepted)",
    )
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = Field(
        description="AI confidence score (0.0-1.0)",
    )
    tier: Optional[str] = Field(
        default=None,
        description="Classification tier (pattern, example, anchor, nli, fallback)",
    )
    reasoning: Optional[str] = Field(
        default=None,
        description="AI's explanation for the suggestion",
    )

    # Resolution context
    model: str = Field(description="AI model name (e.g., 'swen-ml-embeddings')")
    resolved_at: datetime = Field(description="When AI made the decision")
    suggestion_accepted: bool = Field(
        description="Whether the AI suggestion was used",
    )


class TransactionMetadata(BaseModel):
    """Metadata fields not promoted to first-class Transaction properties."""

    model_config = ConfigDict(
        frozen=True,
        extra="ignore",
        json_schema_extra={
            "examples": [
                {
                    "source": "bank_import",
                    "original_purpose": "REWE SAGT DANKE",
                    "bank_reference": "2024121512345",
                },
                {
                    "source": "bank_import",
                    "source_account": "DKB Checking",
                    "destination_account": "DKB Savings",
                    "transfer_identity_hash": "abc123def456",
                },
            ],
        },
    )

    source: TransactionSource = Field(
        description="Origin of the transaction (bank_import, manual, etc.)",
    )

    original_purpose: Optional[str] = Field(
        default=None,
        description="Raw transaction purpose from bank",
    )
    bank_reference: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Bank's reference number",
    )
    source_account: Optional[str] = Field(
        default=None,
        description="Source asset account name (for transfers)",
    )
    destination_account: Optional[str] = Field(
        default=None,
        description="Destination asset account name (for transfers)",
    )
    transfer_identity_hash: Optional[str] = Field(
        default=None,
        description="Canonical hash for transfer deduplication/reconciliation",
    )

    is_opening_balance: bool = Field(
        default=False,
        description="True if this is an opening balance entry",
    )
    opening_balance_iban: Optional[str] = Field(
        default=None,
        max_length=34,
        description="IBAN this opening balance is for (auto-normalized)",
    )

    is_manual_entry: bool = Field(
        default=False,
        description="True if created via manual entry (not bank import)",
    )

    reversed_transaction_id: Optional[str] = Field(
        default=None,
        description="UUID of the original transaction this reverses (if reversal)",
    )

    ai_resolution: Optional[AIResolutionMetadata] = Field(
        default=None,
        description="AI counter-account resolution metadata (if AI was used)",
    )

    @field_validator("opening_balance_iban", mode="before")
    @classmethod
    def normalize_iban_fields(cls, v: Optional[str]) -> Optional[str]:
        return normalize_iban(v)

    def with_updates(self, **kwargs: Any) -> "TransactionMetadata":
        current_data = self.model_dump(exclude_none=True)
        current_data.update(kwargs)
        return TransactionMetadata.model_validate(current_data)


class MetadataKeys:
    """String constants for metadata keys.

    Note: Core fields (source, source_iban, counterparty_iban, is_internal_transfer)
    are now first-class properties on Transaction. These constants are kept for
    fields that remain in metadata.

    Prefer TransactionMetadata for new code.
    """

    # Core (synced with Transaction.source)
    SOURCE = "source"

    # Bank import (informational only)
    ORIGINAL_PURPOSE = "original_purpose"
    BANK_REFERENCE = "bank_reference"

    # Transfer context (for reconciliation tracking)
    SOURCE_ACCOUNT = "source_account"
    DESTINATION_ACCOUNT = "destination_account"
    TRANSFER_IDENTITY_HASH = "transfer_identity_hash"

    # Opening balance
    IS_OPENING_BALANCE = "is_opening_balance"
    OPENING_BALANCE_IBAN = "opening_balance_iban"

    # Manual entry
    IS_MANUAL_ENTRY = "is_manual_entry"

    # Reversal
    REVERSED_TRANSACTION_ID = "reversed_transaction_id"

    # AI resolution
    AI_RESOLUTION = "ai_resolution"

    # Reserved keys that should not be set via raw set_metadata()
    # These keys have special validation or normalization requirements
    RESERVED_KEYS = frozenset(
        {
            SOURCE,
            OPENING_BALANCE_IBAN,
            IS_OPENING_BALANCE,
            IS_MANUAL_ENTRY,
            REVERSED_TRANSACTION_ID,
            AI_RESOLUTION,
            SOURCE_ACCOUNT,
            DESTINATION_ACCOUNT,
            TRANSFER_IDENTITY_HASH,
        },
    )
