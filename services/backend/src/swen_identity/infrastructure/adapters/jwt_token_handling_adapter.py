"""JWT-backed implementation of TokenHandlingPort."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from swen_identity.domain.ports.token_handling_port import TokenHandlingPort
from swen_identity.domain.value_objects.token_payload import TokenPayload
from swen_identity.exceptions import InvalidTokenError


class JWTTokenHandlingAdapter(TokenHandlingPort):
    """Issues and verifies JSON Web Tokens for authentication.

    Handles access tokens (short-lived) and refresh tokens (long-lived).

    Examples
    --------
    >>> adapter = JWTTokenHandlingAdapter(secret_key="your-secret-key")
    >>> token = adapter.create_access_token(user_id, "user@example.com")
    >>> payload = adapter.verify_token(token)
    >>> print(payload.user_id)
    """

    DEFAULT_ACCESS_EXPIRE_HOURS = 24
    DEFAULT_REFRESH_EXPIRE_DAYS = 30
    ALGORITHM = "HS256"

    def __init__(
        self,
        secret_key: str,
        access_token_expire_hours: int = DEFAULT_ACCESS_EXPIRE_HOURS,
        refresh_token_expire_days: int = DEFAULT_REFRESH_EXPIRE_DAYS,
    ):
        """Initialize the adapter.

        Parameters
        ----------
        secret_key
            Secret key for signing tokens. Must be kept secure.
        access_token_expire_hours
            Hours until access token expires (default 24)
        refresh_token_expire_days
            Days until refresh token expires (default 30)
        """
        if not secret_key:
            msg = "JWT secret key cannot be empty"
            raise ValueError(msg)

        self._secret_key = secret_key
        self._access_expire = timedelta(hours=access_token_expire_hours)
        self._refresh_expire = timedelta(days=refresh_token_expire_days)

    def create_access_token(
        self,
        user_id: UUID,
        email: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a short-lived access token."""
        return self._create_token(
            user_id=user_id,
            email=email,
            token_type="access",  # noqa: S106
            expires_delta=expires_delta or self._access_expire,
        )

    def create_refresh_token(
        self,
        user_id: UUID,
        email: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a long-lived refresh token."""
        return self._create_token(
            user_id=user_id,
            email=email,
            token_type="refresh",  # noqa: S106
            expires_delta=expires_delta or self._refresh_expire,
        )

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a JWT token.

        Raises
        ------
        InvalidTokenError
            If token is invalid, expired, or malformed
        """
        try:
            payload = jwt.decode(token, self._secret_key, algorithms=[self.ALGORITHM])

            user_id = UUID(payload["sub"])
            email = payload["email"]
            exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
            token_type = payload.get("type", "access")

            return TokenPayload(
                user_id=user_id,
                email=email,
                exp=exp,
                token_type=token_type,
            )

        except jwt.ExpiredSignatureError as e:
            msg = "Token has expired"
            raise InvalidTokenError(msg) from e
        except jwt.InvalidTokenError as e:
            msg = f"Invalid token: {e}"
            raise InvalidTokenError(msg) from e
        except (KeyError, ValueError) as e:
            msg = f"Malformed token payload: {e}"
            raise InvalidTokenError(msg) from e

    def _create_token(
        self,
        user_id: UUID,
        email: str,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        now = datetime.now(tz=timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": str(user_id),
            "email": email,
            "type": token_type,
            "iat": now,
            "exp": expire,
        }

        return jwt.encode(payload, self._secret_key, algorithm=self.ALGORITHM)
