"""DTOs for data export."""

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from swen.domain.accounting.aggregates import Transaction
from swen.domain.accounting.entities import Account
from swen.domain.integration.entities import AccountMapping


@dataclass(frozen=True)
class TransactionExportDTO:
    """DTO for exporting a transaction."""

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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "counterparty": self.counterparty,
            "counterparty_iban": self.counterparty_iban,
            "source": self.source,
            "source_iban": self.source_iban,
            "is_internal_transfer": self.is_internal_transfer,
            "amount": self.amount,
            "currency": self.currency,
            "debit_account": self.debit_account,
            "credit_account": self.credit_account,
            "status": self.status,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    @classmethod
    def from_transaction(cls, txn: Transaction) -> "TransactionExportDTO":
        amount = Decimal(0)
        amount_currency = "EUR"
        debit_account = ""
        credit_account = ""

        for entry in txn.entries:
            if entry.is_debit():
                debit_account = f"{entry.account.account_number} - {entry.account.name}"
                amount = entry.debit.amount
                amount_currency = entry.debit.currency.code
            else:
                credit_account = (
                    f"{entry.account.account_number} - {entry.account.name}"
                )

        return cls(
            id=str(txn.id),
            date=txn.date.strftime("%Y-%m-%d"),
            description=txn.description,
            counterparty=txn.counterparty or "",
            counterparty_iban=txn.counterparty_iban or "",
            source=txn.source.value,
            source_iban=txn.source_iban or "",
            is_internal_transfer=txn.is_internal_transfer,
            amount=float(amount),
            currency=amount_currency,
            debit_account=debit_account,
            credit_account=credit_account,
            status="posted" if txn.is_posted else "draft",
            metadata=json.dumps(txn.metadata_raw) if txn.metadata_raw else "",
            created_at=txn.created_at.isoformat(),
        )


@dataclass(frozen=True)
class AccountExportDTO:
    """DTO for exporting an account."""

    id: str
    account_number: str
    name: str
    type: str
    currency: str
    is_active: bool
    parent_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "account_number": self.account_number,
            "name": self.name,
            "type": self.type,
            "currency": self.currency,
            "is_active": self.is_active,
            "parent_id": self.parent_id,
            "created_at": self.created_at,
        }

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


@dataclass(frozen=True)
class MappingExportDTO:
    """DTO for exporting a bank account mapping."""

    id: str
    iban: str
    account_name: str
    accounting_account_id: str
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "iban": self.iban,
            "account_name": self.account_name,
            "accounting_account_id": self.accounting_account_id,
            "created_at": self.created_at,
        }

    @classmethod
    def from_mapping(cls, mapping: AccountMapping) -> "MappingExportDTO":
        return cls(
            id=str(mapping.id),
            iban=mapping.iban,
            account_name=mapping.account_name,
            accounting_account_id=str(mapping.accounting_account_id),
            created_at=mapping.created_at.isoformat() if mapping.created_at else "",
        )


@dataclass(frozen=True)
class ExportResult:
    """Result containing exported data as DTOs."""

    transactions: list[TransactionExportDTO] = field(default_factory=list)
    accounts: list[AccountExportDTO] = field(default_factory=list)
    mappings: list[MappingExportDTO] = field(default_factory=list)

    @property
    def transaction_count(self) -> int:
        return len(self.transactions)

    @property
    def account_count(self) -> int:
        return len(self.accounts)

    @property
    def mapping_count(self) -> int:
        return len(self.mappings)
