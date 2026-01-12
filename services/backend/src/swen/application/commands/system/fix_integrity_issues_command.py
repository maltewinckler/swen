"""Fix integrity issues command - repair database integrity problems."""

from dataclasses import dataclass

from swen.application.ports.system import DatabaseIntegrityPort
from swen.application.queries.system import (
    IntegrityCheckResult,
    IntegrityIssue,
    IssueType,
)


@dataclass(frozen=True)
class FixResult:
    """Result of fixing integrity issues."""

    orphan_transactions_deleted: int = 0
    orphan_imports_deleted: int = 0
    duplicates_skipped: int = 0
    unbalanced_skipped: int = 0

    @property
    def total_fixed(self) -> int:
        return self.orphan_transactions_deleted + self.orphan_imports_deleted

    @property
    def total_skipped(self) -> int:
        return self.duplicates_skipped + self.unbalanced_skipped


class FixIntegrityIssuesCommand:
    """Command to fix database integrity issues.

    Automatically fixes:
    - Orphan transactions (deletes them and their journal entries)
    - Orphan import records (deletes them)

    Requires manual review (not auto-fixed):
    - Duplicate transactions
    - Unbalanced transactions
    """

    def __init__(self, integrity_port: DatabaseIntegrityPort):
        self._port = integrity_port

    async def execute(self, check_result: IntegrityCheckResult) -> FixResult:
        orphan_txn_deleted = 0
        orphan_imports_deleted = 0
        duplicates_skipped = 0
        unbalanced_skipped = 0

        for issue in check_result.issues:
            if issue.issue_type == IssueType.ORPHAN_TRANSACTIONS:
                orphan_txn_deleted = await self._fix_orphan_transactions(issue)

            elif issue.issue_type == IssueType.ORPHAN_IMPORTS:
                orphan_imports_deleted = await self._fix_orphan_imports(issue)

            elif issue.issue_type == IssueType.DUPLICATE_TRANSACTIONS:
                duplicates_skipped = issue.count

            elif issue.issue_type == IssueType.UNBALANCED_TRANSACTIONS:
                unbalanced_skipped = issue.count

        return FixResult(
            orphan_transactions_deleted=orphan_txn_deleted,
            orphan_imports_deleted=orphan_imports_deleted,
            duplicates_skipped=duplicates_skipped,
            unbalanced_skipped=unbalanced_skipped,
        )

    async def _fix_orphan_transactions(self, issue: IntegrityIssue) -> int:
        if not issue.affected_ids:
            return 0

        return await self._port.delete_transactions_with_entries(issue.affected_ids)

    async def _fix_orphan_imports(self, issue: IntegrityIssue) -> int:
        if not issue.affected_ids:
            return 0

        return await self._port.delete_import_records(issue.affected_ids)
