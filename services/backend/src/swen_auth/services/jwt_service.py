"""JWT token service.

Provides JWT token creation and verification for authentication.
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt

from swen_auth.exceptions import InvalidTokenError
from swen_auth.schemas import TokenPayload


class JWTService:
    """Service for JWT token creation and verification.

    Handles access tokens (short-lived) and refresh tokens (long-lived)
    for user authentication.

    Examples
    --------
    >>> service = JWTService(secret_key="your-secret-key")
    >>> token = service.create_access_token(user_id, "user@example.com")
    >>> payload = service.verify_token(token)
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
        """Initialize the JWT service.

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
        """Create a short-lived access token.

        Parameters
        ----------
        user_id
            The user's unique identifier
        email
            The user's email address
        expires_delta
            Custom expiration time (optional)

        Returns
        -------
        The encoded JWT token string
        """
        return self._create_token(
            user_id=user_id,
            email=email,
            token_type="access",
            expires_delta=expires_delta or self._access_expire,
        )

    def create_refresh_token(
        self,
        user_id: UUID,
        email: str,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a long-lived refresh token.

        Refresh tokens are used to obtain new access tokens without
        requiring the user to log in again.

        Parameters
        ----------
        user_id
            The user's unique identifier
        email
            The user's email address
        expires_delta
            Custom expiration time (optional)

        Returns
        -------
        The encoded JWT token string
        """
        return self._create_token(
            user_id=user_id,
            email=email,
            token_type="refresh",
            expires_delta=expires_delta or self._refresh_expire,
        )

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a JWT token.

        Parameters
        ----------
        token
            The JWT token string to verify

        Returns
        -------
        TokenPayload containing the decoded data

        Raises
        ------
        InvalidTokenError
            If token is invalid, expired, or malformed
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self.ALGORITHM],
            )

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
            raise InvalidTokenError("Token has expired") from e
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Invalid token: {e}") from e
        except (KeyError, ValueError) as e:
            raise InvalidTokenError(f"Malformed token payload: {e}") from e

    def _create_token(
        self,
        user_id: UUID,
        email: str,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        """Create a JWT token with the given parameters.

        Parameters
        ----------
        user_id
            The user's unique identifier
        email
            The user's email address
        token_type
            Either "access" or "refresh"
        expires_delta
            Time until token expires

        Returns
        -------
        The encoded JWT token string
        """
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

