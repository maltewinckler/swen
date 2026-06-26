"""DTOs for Excel report export."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, computed_field

from swen.application.analytics.dtos.analytics_dto import (
    BreakdownItem,
    MonthComparisonResult,
    TimeSeriesDataPoint,
)
from swen.application.analytics.dtos.export_dto import (
    AccountExportDTO,
)


class AccountBalanceSummary(BaseModel):
    """Account balance for dashboard overview."""

    model_config = ConfigDict(frozen=True)

    account_name: str
    account_number: str
    balance: Decimal
    currency: str


class TransactionExportRowDTO(BaseModel):
    """Enhanced transaction row with full bank metadata for Excel export."""

    model_config = ConfigDict(frozen=True)

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


class DashboardSummaryDTO(BaseModel):
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

    account_balances: list[AccountBalanceSummary] = []
    top_expenses: list[BreakdownItem] = []
    month_comparison: MonthComparisonResult | None = None
    net_worth_trend: list[TimeSeriesDataPoint] = []

    transaction_count: int = 0
    posted_count: int = 0
    draft_count: int = 0


class MappingExportRowDTO(BaseModel):
    """Enhanced mapping row for Excel export with resolved account name."""

    model_config = ConfigDict(frozen=True)

    iban: str
    bank_account_name: str
    accounting_account_name: str
    accounting_account_number: str
    created_at: str

    @classmethod
    def column_headers(cls) -> list[str]:
        return [
            "IBAN",
            "Bank Account Name",
            "Linked Accounting Account",
            "Created",
        ]

    def to_row(self) -> list[str]:
        return [
            self.iban,
            self.bank_account_name,
            f"{self.accounting_account_number} - {self.accounting_account_name}",
            self.created_at,
        ]


class ExportReportData(BaseModel):
    """Complete data structure for Excel report generation."""

    summary: DashboardSummaryDTO
    transactions: list[TransactionExportRowDTO]
    accounts: list[AccountExportDTO]
    mappings: list[MappingExportRowDTO]

    @computed_field
    @property
    def transaction_count(self) -> int:
        return len(self.transactions)

    @computed_field
    @property
    def account_count(self) -> int:
        return len(self.accounts)

    @computed_field
    @property
    def mapping_count(self) -> int:
        return len(self.mappings)
