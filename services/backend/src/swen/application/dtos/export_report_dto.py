"""DTOs for Excel report export."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from swen.application.dtos.analytics import (
    BreakdownItem,
    MonthComparisonResult,
    TimeSeriesDataPoint,
)
from swen.application.dtos.export_dto import (
    AccountExportDTO,
)


@dataclass(frozen=True)
class AccountBalanceSummary:
    """Account balance for dashboard overview."""

    account_name: str
    account_number: str
    balance: Decimal
    currency: str


@dataclass(frozen=True)
class TransactionExportRowDTO:
    """Enhanced transaction row with full bank metadata for Excel export."""

    id: str
    date: str
    description: str
    counterparty: str
    amount: float
    currency: str
    debit_account: str
    credit_account: str
    status: str

    source: str  # bank_import, manual, opening_balance, etc.
    source_iban: str  # The synced bank account IBAN
    counterparty_iban: str  # Counterparty's IBAN
    is_internal_transfer: bool

    original_purpose: str  # Raw bank purpose text
    bank_reference: str  # Bank's transaction reference

    # AI resolution info
    ai_suggested_account: str
    ai_confidence: float | None
    ai_accepted: bool | None

    def to_row(self) -> list[Any]:
        return [
            self.date,
            self.description,
            self.counterparty,
            self.counterparty_iban,
            self.amount,
            self.currency,
            self.debit_account,
            self.credit_account,
            self.status,
            self.source,
            self.source_iban,
            "Yes" if self.is_internal_transfer else "No",
            self.original_purpose,
            self.bank_reference,
            self.ai_suggested_account or "",
            f"{self.ai_confidence:.0%}" if self.ai_confidence is not None else "",
            "Yes" if self.ai_accepted else ("No" if self.ai_accepted is False else ""),
        ]

    @classmethod
    def column_headers(cls) -> list[str]:
        return [
            "Date",
            "Description",
            "Counterparty",
            "Counterparty IBAN",
            "Amount",
            "Currency",
            "Debit Account",
            "Credit Account",
            "Status",
            "Source",
            "Source IBAN",
            "Internal Transfer",
            "Original Purpose",
            "Bank Reference",
            "AI Suggested",
            "AI Confidence",
            "AI Accepted",
        ]


@dataclass
class DashboardSummaryDTO:
    """Summary data for the dashboard overview sheet."""

    report_title: str
    period_label: str
    start_date: date | None
    end_date: date | None
    generated_at: datetime
    currency: str = "EUR"

    total_income: Decimal = Decimal("0")
    total_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")
    savings_rate: Decimal = Decimal("0")  # percentage (0-100)
    net_worth: Decimal = Decimal("0")

    account_balances: list[AccountBalanceSummary] = field(default_factory=list)
    top_expenses: list[BreakdownItem] = field(default_factory=list)
    month_comparison: MonthComparisonResult | None = None
    net_worth_trend: list[TimeSeriesDataPoint] = field(default_factory=list)

    transaction_count: int = 0
    posted_count: int = 0
    draft_count: int = 0


@dataclass(frozen=True)
class MappingExportRowDTO:
    """Enhanced mapping row for Excel export with resolved account name."""

    iban: str
    bank_account_name: str
    accounting_account_name: str
    accounting_account_number: str
    created_at: str

    def to_row(self) -> list[str]:
        return [
            self.iban,
            self.bank_account_name,
            f"{self.accounting_account_number} - {self.accounting_account_name}",
            self.created_at,
        ]

    @classmethod
    def column_headers(cls) -> list[str]:
        return [
            "IBAN",
            "Bank Account Name",
            "Linked Accounting Account",
            "Created",
        ]


@dataclass
class ExportReportData:
    """Complete data structure for Excel report generation."""

    summary: DashboardSummaryDTO
    transactions: list[TransactionExportRowDTO]
    accounts: list[AccountExportDTO]
    mappings: list[MappingExportRowDTO]

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)

    @property
    def account_count(self) -> int:
        return len(self.accounts)

    @property
    def mapping_count(self) -> int:
        return len(self.mappings)
