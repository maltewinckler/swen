from pydantic import BaseModel, ConfigDict


class CredentialDTO(BaseModel):
    """Credential information for display."""

    model_config = ConfigDict(frozen=True)

    credential_id: str
    blz: str
    label: str
