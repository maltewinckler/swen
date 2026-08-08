import hashlib
import logging
import secrets
from datetime import timedelta

from swen.domain.shared.time import utc_now
from swen_identity.domain import (
    PasswordResetTokenRepository,
    UserCredentialRepository,
    UserRepository,
)
from swen_identity.domain.ports import EmailNotificationPort, PasswordHashingPort
from swen_identity.exceptions import InvalidResetTokenError

logger = logging.getLogger(__name__)


class PasswordResetService:
    """Service for handling password reset requests and token validation."""

    MAX_RESETS_PER_DAY = 3
    TOKEN_EXPIRY_HOURS = 1

    def __init__(  # noqa: PLR0913
        self,
        user_repository: UserRepository,
        token_repository: PasswordResetTokenRepository,
        credential_repository: UserCredentialRepository,
        password_hashing_port: PasswordHashingPort,
        email_notification_port: EmailNotificationPort,
        frontend_base_url: str,
    ):
        self._user_repo = user_repository
        self._token_repo = token_repository
        self._credential_repo = credential_repository
        self._password_hashing_port = password_hashing_port
        self._email_notification_port = email_notification_port
        self._frontend_base_url = frontend_base_url.rstrip("/")

    def _hash_token(self, raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()

    async def request_reset(self, email: str) -> None:
        user = await self._user_repo.find_by_email(email)
        if not user:
            # Silent fail to prevent email enumeration
            logger.debug("Password reset requested for unknown email: %s", email)
            return

        # Rate limit check
        since = utc_now() - timedelta(days=1)
        count = await self._token_repo.count_recent_for_user(user.id, since)
        if count >= self.MAX_RESETS_PER_DAY:
            logger.warning("Rate limit exceeded for password reset: %s", email)
            # Still silent fail for security
            return

        # Generate secure token
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)
        expires_at = utc_now() + timedelta(hours=self.TOKEN_EXPIRY_HOURS)

        # Invalidate old tokens and create new one
        await self._token_repo.invalidate_all_for_user(user.id)
        await self._token_repo.create(user.id, token_hash, expires_at)

        # Send email with reset link
        reset_link = f"{self._frontend_base_url}/reset-password?token={raw_token}"
        try:
            self._email_notification_port.send_password_reset_email(
                to_email=email, reset_link=reset_link
            )
            logger.info("Password reset email sent to %s", email)
        except Exception as e:
            # Don't raise as we already created the token
            logger.error("Failed to send password reset email: %s", e)

    async def reset_password(self, token: str, new_password: str) -> None:
        token_hash = self._hash_token(token)
        reset_token = await self._token_repo.find_valid_by_hash(token_hash)

        if not reset_token:
            raise InvalidResetTokenError

        now = utc_now()
        if reset_token.is_expired(now):
            raise InvalidResetTokenError

        if reset_token.is_used():
            raise InvalidResetTokenError

        # Update password
        new_hash = self._password_hashing_port.hash(new_password)
        await self._credential_repo.save(
            user_id=reset_token.user_id,
            password_hash=new_hash,
        )

        # Mark token as used
        await self._token_repo.mark_used(reset_token.id)
        logger.info("Password reset completed for user: %s", reset_token.user_id)
