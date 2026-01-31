"""ML Service API contracts.

This package defines the API contract between the SWEN backend and the ML service.
See docs/_specs/PRD_CLASSIFICATION.md Section 3.2 for details.
"""

from swen_ml_contracts.accounts import EmbedAccountsRequest, EmbedAccountsResponse
from swen_ml_contracts.classify import (
    Classification,
    ClassificationStats,
    ClassificationTier,
    ClassifyBatchRequest,
    ClassifyBatchResponse,
    TransactionInput,
)
from swen_ml_contracts.common import AccountOption
from swen_ml_contracts.examples import (
    DeleteAccountResponse,
    DeleteUserResponse,
    HealthResponse,
    StoreExampleRequest,
    StoreExampleResponse,
    UserStatsResponse,
)

__all__ = [
    # Common
    "AccountOption",
    # Classification (batch API)
    "TransactionInput",
    "ClassifyBatchRequest",
    "Classification",
    "ClassificationStats",
    "ClassificationTier",
    "ClassifyBatchResponse",
    # Examples
    "StoreExampleRequest",
    "StoreExampleResponse",
    "UserStatsResponse",
    "DeleteAccountResponse",
    "DeleteUserResponse",
    # Accounts
    "EmbedAccountsRequest",
    "EmbedAccountsResponse",
    # Health
    "HealthResponse",
]
