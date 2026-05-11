from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class CredentialToStore(BaseModel):
    """Request schema for storing new credentials."""

    blz: str = Field(..., min_length=8, max_length=8, pattern=r"^\d{8}$")
    username: str = Field(..., min_length=1, max_length=100)
    pin: str = Field(..., min_length=1, max_length=100)
    tan_method: Optional[str] = Field(default=None, max_length=10)
    tan_medium: Optional[str] = Field(default=None, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "blz": "50031000",
                "username": "my_username",
                "pin": "my_secret_pin",
                "tan_method": None,
                "tan_medium": None,
            },
        },
    )


class CredentialToUpdate(BaseModel):
    """Request schema for partially updating stored credentials."""

    username: Optional[str] = Field(None, min_length=1, max_length=100)
    pin: Optional[str] = Field(None, min_length=1, max_length=100)
    tan_method: Optional[str] = Field(None, max_length=10)
    tan_medium: Optional[str] = Field(None, max_length=100)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "tan_method": "946",
                "tan_medium": "SecureGo",
            },
        },
    )


class StoredCredential(BaseModel):
    """Response schema for credential metadata (no sensitive data)."""

    credential_id: str = Field(..., description="Unique credential identifier")
    blz: str = Field(..., description="Bank code (BLZ) - 8 digits")
    label: str = Field(..., description="User-friendly label (typically bank name)")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "credential_id": "cred_abc123def456",
                "blz": "50031000",
                "label": "Triodos Bank N.V. Deutschland",
            },
        },
    )


class StoredCredentialList(BaseModel):
    """Response schema for listing stored credentials."""

    credentials: list[StoredCredential] = Field(..., description="Stored cred ids")

    @computed_field
    @property
    def total(self) -> int:
        """Total number of stored credentials."""
        return len(self.credentials)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "credentials": [
                    {
                        "credential_id": "cred_abc123def456",
                        "blz": "50031000",
                        "label": "Triodos Bank N.V. Deutschland",
                    },
                    {
                        "credential_id": "cred_xyz789ghi012",
                        "blz": "20000000",
                        "label": "Commerzbank AG",
                    },
                ],
                "total": 2,
            },
        },
    )
