"""Authentication schemas for request/response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

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

    The refresh token is sent as an HttpOnly cookie, never in the response body.
    """

    access_token: str
    token_type: str = Field(default="bearer")
    expires_in: int

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NT[...]",
                "token_type": "bearer",
                "expires_in": 3600,
            },
        },
    )


class AuthResponse(BaseModel):
    """Response schema for authentication (login/register).

    The refresh token is sent as an HttpOnly cookie.
    """

    user: UserResponse
    access_token: str
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
