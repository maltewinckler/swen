"""Port for sending identity-related email notifications."""

from abc import ABC, abstractmethod


class EmailNotificationPort(ABC):
    """Port for sending identity-related transactional emails."""

    @abstractmethod
    def send_password_reset_email(self, to_email: str, reset_link: str) -> None:
        """Send a password reset email with the given reset link."""
