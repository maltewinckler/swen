"""Account entity."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from swen.domain.accounting.entities.account_type import AccountType
from swen.domain.accounting.value_objects import Currency, Money
from swen.domain.shared.exceptions import ValidationError
from swen.domain.shared.iban import normalize_iban
from swen.domain.shared.time import utc_now


class Account:
    """
    A financial account in our accounting system.

    Multi-User Support:
    - Each account belongs to exactly one user
    - Account IDs are stable UUIDs (not derived from account_number/iban)
    - Uniqueness is enforced at persistence level (e.g. per-user account_number,
        per-user iban)
    """

    def __init__(  # NOQA: PLR0913
        self,
        name: str,
        account_type: AccountType,
        account_number: str,
        user_id: UUID,
        iban: Optional[str] = None,
        default_currency: Optional[Currency] = None,
        description: Optional[str] = None,
        id: Optional[UUID] = None,
        is_active: bool = True,
        created_at: Optional[datetime] = None,
        parent_id: Optional[UUID] = None,
    ):
        """
        Initialize a new account.

        Parameters
        ----------
        name
            Human-readable account name
        account_type
            Type of account (Asset, Liability, Equity, etc.)
        account_number
            Display/account code per user (e.g., "4900", "1001")
        user_id
            Owner user ID (required for multi-user support)
        iban
            Optional IBAN for bank/external asset accounts (normalized, no spaces)
        default_currency
            Currency for this account (defaults to EUR)
        description
            Optional description with examples of typical transactions
            (e.g., "Supermarkets, groceries: REWE, Lidl, EDEKA")
        id
            Account ID (generated if not provided, used for reconstitution)
        is_active
            Whether account is active (defaults to True)
        created_at
            Creation timestamp (defaults to now, used for reconstitution)
        parent_id
            Parent account ID for hierarchy (defaults to None)
        """
        self._user_id = user_id
        self._iban = normalize_iban(iban)
        self._id = id if id is not None else uuid4()
        self._name = name
        self._account_type = account_type
        self._account_number = account_number
        self._default_currency = default_currency or Currency.default()
        self._description = description
        self._is_active = is_active
        self._created_at = created_at or utc_now()
        self._parent_id = parent_id

    @classmethod
    def reconstitute(  # NOQA: PLR0913
        cls,
        id: UUID,
        user_id: UUID,
        name: str,
        account_type: AccountType,
        account_number: str,
        default_currency: Currency,
        is_active: bool,
        created_at: datetime,
        iban: Optional[str] = None,
        description: Optional[str] = None,
        parent_id: Optional[UUID] = None,
    ) -> "Account":
        return cls(
            id=id,
            user_id=user_id,
            name=name,
            account_type=account_type,
            account_number=account_number,
            default_currency=default_currency,
            is_active=is_active,
            created_at=created_at,
            iban=iban,
            description=description,
            parent_id=parent_id,
        )

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def account_type(self) -> AccountType:
        return self._account_type

    @property
    def account_number(self) -> str:
        return self._account_number

    @property
    def iban(self) -> Optional[str]:
        return self._iban

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def parent_id(self) -> Optional[UUID]:
        return self._parent_id

    @property
    def default_currency(self) -> Currency:
        return self._default_currency

    @property
    def description(self) -> Optional[str]:
        return self._description

    def set_description(self, description: Optional[str]) -> None:
        self._description = description.strip() if description else None

    def set_parent(self, parent_account: "Account") -> None:
        """Set parent account for account hierarchy.

        Business Rules:
        - Parent must be same account type
        - Parent must belong to same user
        - Cannot create circular references
        - Cannot set self as parent
        """
        if parent_account.account_type != self._account_type:
            msg = "Parent account must be of the same account type"
            raise ValidationError(msg)
        if parent_account.user_id != self._user_id:
            msg = "Parent account must belong to the same user"
            raise ValidationError(msg)
        if parent_account.id == self._id:
            msg = "Account cannot be its own parent"
            raise ValidationError(msg)

        # Circular reference check requires access to AccountRepository
        # Thus, it must be handled by the domain service
        self._parent_id = parent_account.id

    def remove_parent(self) -> None:
        self._parent_id = None

    def is_sub_account(self) -> bool:
        return self._parent_id is not None

    def is_parent_account(self) -> bool:
        """CANNOT BE IMPLEMENTED HERE: Must have knowledge about repository."""
        msg = "is_parent_account requires repository, implemented in domain services."
        raise NotImplementedError(msg)

    def deactivate(self) -> None:
        self._is_active = False

    def activate(self) -> None:
        self._is_active = True

    def rename(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            msg = "Account name cannot be empty"
            raise ValidationError(msg)
        self._name = new_name.strip()

    def change_account_number(self, new_number: str) -> None:
        # Uniqueness validation must be done at the command/service level
        # since it requires repository access.
        if not new_number or not new_number.strip():
            msg = "Account number cannot be empty"
            raise ValidationError(msg)
        self._account_number = new_number.strip()

    def can_accept_transaction(self, amount: Money) -> bool:
        # For now, simple rule: asset accounts should maintain positive balance
        # In future, this could include credit limits, overdraft rules, etc.
        if self._account_type == AccountType.ASSET:
            return amount.amount >= Decimal(0)
        return True

    def is_debit_normal(self) -> bool:
        return self._account_type in [AccountType.ASSET, AccountType.EXPENSE]

    def is_credit_normal(self) -> bool:
        return self._account_type in [
            AccountType.LIABILITY,
            AccountType.EQUITY,
            AccountType.INCOME,
        ]

    def __eq__(self, other) -> bool:
        if not isinstance(other, Account):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        return f"{self._name} ({self._account_type.value})"
