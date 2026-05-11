from typing import Optional

from pydantic import BaseModel, ConfigDict

from swen.domain.shared.value_objects import SecureString


class CredentialToStoreDTO(BaseModel):
    """Credential information for storage (including creds)."""

    model_config = ConfigDict(frozen=True)

    blz: str
    username: SecureString
    pin: SecureString
    tan_method: Optional[str]
    tan_medium: Optional[str]


class StoredCredentialDTO(BaseModel):
    """Credential information for display (just ID, no creds)."""

    model_config = ConfigDict(frozen=True)

    credential_id: str
    label: Optional[str]
    blz: str


class StoredCredentialListDTO(BaseModel):
    """List of stored credentials for display."""

    model_config = ConfigDict(frozen=True)

    credentials: list[StoredCredentialDTO]


class UpdateCredentialsDTO(BaseModel):
    """Partial update for existing stored credentials."""

    model_config = ConfigDict(frozen=True)

    blz: str
    username: Optional[SecureString] = None
    pin: Optional[SecureString] = None
    tan_method: Optional[str] = None
    tan_medium: Optional[str] = None
