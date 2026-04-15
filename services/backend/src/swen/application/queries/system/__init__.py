"""System queries. Database integrity, maintenance, and configuration operations."""

from swen.application.queries.system.database_integrity_query import (
    DatabaseIntegrityQuery,
    IntegrityCheckResult,
    IntegrityIssue,
    IssueSeverity,
    IssueType,
)
from swen.application.queries.system.geldstrom_api.get_geldstrom_api_config_query import (  # noqa: E501
    GeldstromApiConfigDTO,
    GetGeldstromApiConfigQuery,
)
from swen.application.queries.system.get_fints_provider_status_query import (
    FintsProviderStatusDTO,
    GetFintsProviderStatusQuery,
)
from swen.application.queries.system.local_fints.get_fints_configuration_query import (
    FinTSConfigDTO,
    GetFinTSConfigurationQuery,
)
from swen.application.queries.system.local_fints.get_fints_configuration_status_query import (  # noqa: E501
    FinTSConfigStatusDTO,
    GetFinTSConfigurationStatusQuery,
)

__all__ = [
    "DatabaseIntegrityQuery",
    "FinTSConfigDTO",
    "FinTSConfigStatusDTO",
    "FintsProviderStatusDTO",
    "GeldstromApiConfigDTO",
    "GetFinTSConfigurationQuery",
    "GetFinTSConfigurationStatusQuery",
    "GetFintsProviderStatusQuery",
    "GetGeldstromApiConfigQuery",
    "IntegrityCheckResult",
    "IntegrityIssue",
    "IssueSeverity",
    "IssueType",
]
