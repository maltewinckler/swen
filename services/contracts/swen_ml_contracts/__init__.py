"""ML Service API contracts."""

from swen_ml_contracts.classify import (
    ClassificationResult,
    ClassifyBatchRequest,
    ClassifyBatchResponse,
    ClassifyRequest,
    ClassifyResponse,
    TransactionInput,
)
from swen_ml_contracts.common import AccountOption
from swen_ml_contracts.examples import (
    AddExampleRequest,
    AddExampleResponse,
    DeleteAccountResponse,
    DeleteUserResponse,
    EmbedAccountsRequest,
    EmbedAccountsResponse,
    HealthResponse,
    UserStatsResponse,
)

__all__ = [
    "AccountOption",
    "TransactionInput",
    "ClassifyRequest",
    "ClassifyBatchRequest",
    "ClassificationResult",
    "ClassifyResponse",
    "ClassifyBatchResponse",
    "AddExampleRequest",
    "AddExampleResponse",
    "EmbedAccountsRequest",
    "EmbedAccountsResponse",
    "UserStatsResponse",
    "DeleteAccountResponse",
    "DeleteUserResponse",
    "HealthResponse",
]
