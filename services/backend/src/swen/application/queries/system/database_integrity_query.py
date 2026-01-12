"""Database integrity query. Check for data integrity issues."""

from dataclasses import dataclass, field
from enum import Enum

from swen.application.ports.system import DatabaseIntegrityPort
from swen.domain.accounting.value_objects import MetadataKeys


class IssueSeverity(str, Enum):
    """Severity of an integrity issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class IssueType(str, Enum):
    """Type of integrity issue."""

    ORPHAN_TRANSACTIONS = "orphan_transactions"
    DUPLICATE_TRANSACTIONS = "duplicate_transactions"
    ORPHAN_IMPORTS = "orphan_imports"
    UNBALANCED_TRANSACTIONS = "unbalanced_transactions"


@dataclass(frozen=True)
class IntegrityIssue:
    """Represents a database integrity issue."""

    issue_type: IssueType
    severity: IssueSeverity
    description: str
    affected_ids: tuple[str, ...] = field(default_factory=tuple)

    @property
    def count(self) -> int:
        return len(self.affected_ids)


@dataclass(frozen=True)
class IntegrityCheckResult:
    """Result of database integrity check."""

    issues: tuple[IntegrityIssue, ...] = field(default_factory=tuple)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == IssueSeverity.ERROR for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == IssueSeverity.WARNING for i in self.issues)

    @property
    def is_healthy(self) -> bool:
        return len(self.issues) == 0

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING)


class DatabaseIntegrityQuery:
    """Query to check database integrity."""

    def __init__(self, integrity_port: DatabaseIntegrityPort):
        self._port = integrity_port

    async def execute(self) -> IntegrityCheckResult:
        issues: list[IntegrityIssue] = []

        if issue := await self._check_orphan_transactions():
            issues.append(issue)

        if issue := await self._check_duplicate_transactions():
            issues.append(issue)

        if issue := await self._check_orphan_imports():
            issues.append(issue)

        if issue := await self._check_unbalanced_transactions():
            issues.append(issue)

        return IntegrityCheckResult(issues=tuple(issues))

    async def _check_orphan_transactions(self) -> IntegrityIssue | None:
        orphan_ids = await self._port.find_orphan_transaction_ids(
            opening_balance_metadata_key=MetadataKeys.IS_OPENING_BALANCE,
            source_metadata_key=MetadataKeys.SOURCE,
        )

        if not orphan_ids:
            return None

        return IntegrityIssue(
            issue_type=IssueType.ORPHAN_TRANSACTIONS,
            severity=IssueSeverity.WARNING,
            description=(
                f"Found {len(orphan_ids)} accounting transaction(s) without "
                "import records "
                "(may be manually added or from a bug)"
            ),
            affected_ids=orphan_ids,
        )

    async def _check_duplicate_transactions(self) -> IntegrityIssue | None:
        duplicate_ids = await self._port.find_duplicate_transaction_ids()

        if not duplicate_ids:
            return None

        return IntegrityIssue(
            issue_type=IssueType.DUPLICATE_TRANSACTIONS,
            severity=IssueSeverity.ERROR,
            description=(
                "Found duplicate transactions (same date, description, and amount)"
            ),
            affected_ids=duplicate_ids,
        )

    async def _check_orphan_imports(self) -> IntegrityIssue | None:
        orphan_ids = await self._port.find_orphan_import_ids()

        if not orphan_ids:
            return None

        return IntegrityIssue(
            issue_type=IssueType.ORPHAN_IMPORTS,
            severity=IssueSeverity.WARNING,
            description=(
                f"Found {len(orphan_ids)} import record(s) pointing to "
                "deleted transactions"
            ),
            affected_ids=orphan_ids,
        )

    async def _check_unbalanced_transactions(self) -> IntegrityIssue | None:
        unbalanced_ids = await self._port.find_unbalanced_transaction_ids()

        if not unbalanced_ids:
            return None

        return IntegrityIssue(
            issue_type=IssueType.UNBALANCED_TRANSACTIONS,
            severity=IssueSeverity.ERROR,
            description=(
                f"Found {len(unbalanced_ids)} transaction(s) where debits "
                "don't equal credits"
            ),
            affected_ids=unbalanced_ids,
        )
