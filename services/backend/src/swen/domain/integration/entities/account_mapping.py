"""Account mapping entity for linking bank accounts to accounting accounts."""

from datetime import datetime

from swen.domain.shared.time import utc_now
from uuid import UUID, uuid5

from swen.domain.shared.iban import normalize_iban

ACCOUNT_MAPPING_NAMESPACE = UUID("a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d")


class AccountMapping:
    """
    Links a bank account (IBAN) to an accounting asset account.

    This is the user's configuration that defines which accounting account
    represents each external bank connection. For example:
    - IBAN DE89370400440532013000 -> "DKB Checking Account" (Asset)
    - IBAN DE89370400440532013001 -> "Savings Account" (Asset)
    """

    def __init__(
        self,
        iban: str,
        accounting_account_id: UUID,
        account_name: str,
        user_id: UUID,
        is_active: bool = True,
    ):
        self._user_id = user_id
        normalized_iban = normalize_iban(iban)
        self._iban = normalized_iban or ""  # Normalize IBAN (spaces removed, upper)
        self._accounting_account_id = accounting_account_id

        # Generate deterministic UUID based on user_id + IBAN + accounting account ID
        # This ensures the same mapping always gets the same ID per user
        name = f"{user_id}:{self._iban}:{accounting_account_id!s}"
        self._id = uuid5(ACCOUNT_MAPPING_NAMESPACE, name)

        self._account_name = account_name.strip()
        self._is_active = is_active
        self._created_at = utc_now()
        self._updated_at = utc_now()

        self._validate()

    @property
    def id(self) -> UUID:
        return self._id

    @property
    def user_id(self) -> UUID:
        return self._user_id

    @property
    def iban(self) -> str:
        return self._iban

    @property
    def accounting_account_id(self) -> UUID:
        return self._accounting_account_id

    @property
    def account_name(self) -> str:
        return self._account_name

    @property
    def is_active(self) -> bool:
        return self._is_active

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def updated_at(self) -> datetime:
        return self._updated_at

    def _validate(self) -> None:
        if not self._iban:
            msg = "IBAN cannot be empty"
            raise ValueError(msg)

        # Basic IBAN format validation (15-34 characters, starts with 2 letters)
        if len(self._iban) < 15 or len(self._iban) > 34:
            msg = f"Invalid IBAN length: {len(self._iban)}"
            raise ValueError(msg)

        if not self._iban[:2].isalpha():
            msg = "IBAN must start with 2 letter country code"
            raise ValueError(msg)

        if not self._account_name:
            msg = "Account name cannot be empty"
            raise ValueError(msg)

    def update_account_name(self, new_name: str) -> None:
        if not new_name or not new_name.strip():
            msg = "Account name cannot be empty"
            raise ValueError(msg)

        self._account_name = new_name.strip()
        self._updated_at = utc_now()

    def deactivate(self) -> None:
        self._is_active = False
        self._updated_at = utc_now()

    def activate(self) -> None:
        self._is_active = True
        self._updated_at = utc_now()

    def update_accounting_account(self, new_account_id: UUID) -> None:
        # This changes the identity of the mapping since the ID is based on
        # user_id + IBAN + accounting_account_id. The ID will be regenerated.
        # This should be used carefully as it affects all future imports.
        # Existing transactions remain linked to their original accounts.
        # TODO: CHECK WHETHER THIS HAS CORRECT USER BEHAVIOUR
        self._accounting_account_id = new_account_id

        # Regenerate ID since it's based on user_id + IBAN + accounting_account_id
        name = f"{self._user_id}:{self._iban}:{new_account_id!s}"
        self._id = uuid5(ACCOUNT_MAPPING_NAMESPACE, name)

        self._updated_at = utc_now()

    def __eq__(self, other) -> bool:
        if not isinstance(other, AccountMapping):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)

    def __str__(self) -> str:
        status = "ACTIVE" if self._is_active else "INACTIVE"
        return f"AccountMapping[{status}]: {self._account_name} ({self._iban})"
