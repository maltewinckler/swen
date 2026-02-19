"""System queries. Database integrity, maintenance, and configuration operations."""

from swen.application.queries.system.database_integrity_query import (
    DatabaseIntegrityQuery,
    IntegrityCheckResult,
    IntegrityIssue,
    IssueSeverity,
    IssueType,
)
from swen.application.queries.system.get_fints_configuration_query import (
    FinTSConfigDTO,
    GetFinTSConfigurationQuery,
)
from swen.application.queries.system.get_fints_configuration_status_query import (
    FinTSConfigStatusDTO,
    GetFinTSConfigurationStatusQuery,
)

__all__ = [
    "DatabaseIntegrityQuery",
    "FinTSConfigDTO",
    "FinTSConfigStatusDTO",
    "GetFinTSConfigurationQuery",
    "GetFinTSConfigurationStatusQuery",
    "IntegrityCheckResult",
    "IntegrityIssue",
    "IssueSeverity",
    "IssueType",
]
