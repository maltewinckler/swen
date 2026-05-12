from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CreateUserRequest(BaseModel):
    """Request schema for creating a new user."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = "user"


class UpdateRoleRequest(BaseModel):
    """Request schema for updating a user's role."""

    role: str


class UserSummaryResponse(BaseModel):
    """Response schema for a user summary."""

    id: UUID
    email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
