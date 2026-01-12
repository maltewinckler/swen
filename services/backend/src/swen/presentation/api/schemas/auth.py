"""Authentication schemas for request/response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request schema for user registration."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Password (8-128 characters)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            }
        }
    }


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123",
            }
        }
    }


class RefreshRequest(BaseModel):
    """Request schema for token refresh.

    The refresh_token field is optional - if not provided in the request body,
    the server will read it from the HttpOnly cookie instead.
    """

    refresh_token: str | None = Field(
        default=None,
        description="Refresh token (optional - can also be sent via HttpOnly cookie)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }
    }


class ChangePasswordRequest(BaseModel):
    """Request schema for password change."""

    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8-128 characters)",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newSecurePassword456",
            }
        }
    }


class UserResponse(BaseModel):
    """Response schema for user data."""

    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    created_at: datetime = Field(..., description="Account creation timestamp")

    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "created_at": "2024-12-05T10:30:00Z",
            }
        },
    }


class TokenResponse(BaseModel):
    """Response schema for token data.

    Note: refresh_token is deprecated in the response body.
    It is now sent as an HttpOnly cookie for security.
    The field remains for backward compatibility during migration.
    """

    access_token: str = Field(..., description="JWT access token for API requests")
    refresh_token: str | None = Field(
        default=None,
        description="Deprecated: refresh token is now in HttpOnly cookie",
    )
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Access token expiry in seconds (typically 3600)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJleHAiOjE3MzMzOTg2MDB9.xxx",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
    }


class AuthResponse(BaseModel):
    """Response schema for authentication (login/register).

    Note: refresh_token is deprecated in the response body.
    It is now sent as an HttpOnly cookie for security.
    The field remains for backward compatibility during migration.
    """

    user: UserResponse = Field(..., description="Authenticated user data")
    access_token: str = Field(..., description="JWT access token for API requests")
    refresh_token: str | None = Field(
        default=None,
        description="Deprecated: refresh token is now in HttpOnly cookie",
    )
    token_type: str = Field(default="bearer", description="Token type (always 'bearer')")
    expires_in: int = Field(..., description="Access token expiry in seconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "user@example.com",
                    "created_at": "2024-12-05T10:30:00Z",
                },
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
            }
        }
    }

