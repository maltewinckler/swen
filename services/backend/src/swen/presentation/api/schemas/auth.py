"""Authentication schemas for request/response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 characters)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            },
        },
    )


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            },
        },
    )


class RefreshRequest(BaseModel):
    """Request schema for token refresh.

    The refresh_token field is optional - if not provided in the request body,
    the server will read it from the HttpOnly cookie instead.
    """

    refresh_token: str | None = Field(
        default=None,
        description="Refresh token (optional - can also be sent via HttpOnly cookie)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            },
        },
    )


class ChangePasswordRequest(BaseModel):
    """Request schema for changing a user's password."""

    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class ForgotPasswordRequest(BaseModel):
    """Request schema for requesting a password reset email."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request schema for resetting a password with a token."""

    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: UUID
    email: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Response schema for token data.

    Note: refresh_token is deprecated in the response body.
    It is now sent as an HttpOnly cookie for security.
    The field remains for backward compatibility during migration.
    """

    access_token: str
    refresh_token: str | None = Field(
        default=None,
        description="Deprecated: refresh token is now in HttpOnly cookie",
    )
    token_type: str = Field(default="bearer")
    expires_in: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJleHAiOjE3MzMzOTg2MDB9.xxx",
                "token_type": "bearer",
                "expires_in": 3600,
            },
        },
    )


class AuthResponse(BaseModel):
    """Response schema for authentication (login/register).

    Note: refresh_token is deprecated in the response body.
    It is now sent as an HttpOnly cookie for security.
    The field remains for backward compatibility during migration.
    """

    user: UserResponse
    access_token: str
    refresh_token: str | None = Field(
        default=None,
        description="Deprecated: refresh token is now in HttpOnly cookie",
    )
    token_type: str = Field(default="bearer")
    expires_in: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "role": "user",
                    "created_at": "2024-12-05T10:30:00Z",
                },
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
            },
        },
    )
