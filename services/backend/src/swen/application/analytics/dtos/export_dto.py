"""DTOs for data export."""

import json
from typing import Optional

from pydantic import BaseModel, ConfigDict, computed_field

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.accounting.services import TransactionAnalyzer
from swen.domain.integration.entities import AccountMapping


class TransactionExportDTO(BaseModel):
    """DTO for exporting a transaction."""

    model_config = ConfigDict(frozen=True)

    id: str
    date: str
    description: str
    counterparty: str
    counterparty_iban: str
    source: str
    source_iban: str
    is_internal_transfer: bool
    amount: float
    currency: str
    debit_account: str
    credit_account: str
    status: str
    metadata: str
    created_at: str

    @classmethod
    def from_transaction(cls, txn: Transaction) -> "TransactionExportDTO":
        return cls(
            id=str(txn.id),
            date=txn.date.strftime("%Y-%m-%d"),
            description=txn.description,
            counterparty=txn.counterparty or "",
            counterparty_iban=txn.counterparty_iban or "",
            source=txn.source.value,
            source_iban=txn.source_iban or "",
            is_internal_transfer=txn.is_internal_transfer,
            amount=float(TransactionAnalyzer.payment_amount(txn)),
            currency=TransactionAnalyzer.payment_currency(txn),
            debit_account=cls._format_account_name(
                txn, TransactionAnalyzer.debit_account_name(txn)
            ),
            credit_account=cls._format_account_name(
                txn, TransactionAnalyzer.credit_account_name(txn)
            ),
            status="posted" if txn.is_posted else "draft",
            metadata=json.dumps(txn.metadata_raw) if txn.metadata_raw else "",
            created_at=txn.created_at.isoformat(),
        )

    @staticmethod
    def _format_account_name(
        txn: Transaction,
        account_label: Optional[str],
    ) -> str:
        """Format account name with number for export.

        Looks up the account by the label returned from TransactionAnalyzer
        and returns "number - name" format.
        """
        if not account_label:
            return ""

        for entry in txn.entries:
            if entry.account.name == account_label:
                return f"{entry.account.account_number} - {entry.account.name}"

        return account_label


class AccountExportDTO(BaseModel):
    """DTO for exporting an account."""

    model_config = ConfigDict(frozen=True)

    id: str
    account_number: str
    name: str
    type: str
    currency: str
    is_active: bool
    parent_id: str
    created_at: str

    @classmethod
    def from_account(cls, account: Account) -> "AccountExportDTO":
        return cls(
            id=str(account.id),
            account_number=account.account_number,
            name=account.name,
            type=account.account_type.value,
            currency=account.default_currency.code,
            is_active=account.is_active,
            parent_id=str(account.parent_id) if account.parent_id else "",
            created_at=account.created_at.isoformat(),
        )


class MappingExportDTO(BaseModel):
    """DTO for exporting a bank account mapping."""

    model_config = ConfigDict(frozen=True)

    id: str
    iban: str
    account_name: str
    accounting_account_id: str
    created_at: str

    @classmethod
    def from_mapping(cls, mapping: AccountMapping) -> "MappingExportDTO":
        return cls(
            id=str(mapping.id),
            iban=mapping.iban,
            account_name=mapping.account_name,
            accounting_account_id=str(mapping.accounting_account_id),
            created_at=mapping.created_at.isoformat() if mapping.created_at else "",
        )


class ExportResult(BaseModel):
    """Result containing exported data as DTOs."""

    transactions: list[TransactionExportDTO] = []
    accounts: list[AccountExportDTO] = []
    mappings: list[MappingExportDTO] = []

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
