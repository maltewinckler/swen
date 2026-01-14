import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from swen_config.settings import Settings

logger = logging.getLogger(__name__)

PASSWORD_RESET_SUBJECT = "Password Reset Request - SWEN"

PASSWORD_RESET_TEXT = """Hello,

You requested a password reset for your SWEN account.

Click the link below to reset your password (valid for 1 hour):
{reset_link}

If you didn't request this, you can safely ignore this email.

-- SWEN
"""

PASSWORD_RESET_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background-color: #f9fafb; margin: 0; padding: 20px;">
    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <h2 style="color: #111827; margin-top: 0;">Password Reset Request</h2>
        <p style="color: #374151; line-height: 1.6;">You requested a password reset for your SWEN account.</p>
        <p style="color: #374151; line-height: 1.6;">Click the button below to reset your password. This link is valid for 1 hour.</p>
        <p style="margin: 30px 0; text-align: center;">
            <a href="{reset_link}" style="display: inline-block; padding: 14px 28px; background-color: #2563eb; color: #ffffff !important; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px;">Reset Password</a>
        </p>
        <p style="color: #6b7280; font-size: 14px;">Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #2563eb; font-size: 14px;">{reset_link}</p>
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb;">
            <p style="color: #9ca3af; font-size: 13px; margin: 0;">If you didn't request this, you can safely ignore this email.</p>
            <p style="color: #9ca3af; font-size: 13px; margin-top: 8px;">— SWEN</p>
        </div>
    </div>
</body>
</html>
"""


class EmailService:
    def __init__(self, settings: Settings):
        self._settings = settings

    def _create_message(
        self,
        to_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> MIMEMultipart:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self._settings.smtp_from_name} <{self._settings.smtp_from_email}>"
        msg["To"] = to_email

        msg.attach(MIMEText(text_body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        return msg

    def _send_email(self, to_email: str, message: MIMEMultipart) -> None:
        if not self._settings.smtp_enabled:
            logger.warning("SMTP disabled, email not sent to %s", to_email)
            return

        if not self._settings.smtp_host:
            logger.error("SMTP host not configured")
            return

        smtp_password = (
            self._settings.smtp_password.get_secret_value()
            if self._settings.smtp_password
            else ""
        )

        try:
            if self._settings.smtp_use_tls and not self._settings.smtp_starttls:
                # Implicit TLS (port 465)
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(
                    self._settings.smtp_host,
                    self._settings.smtp_port,
                    context=context,
                ) as server:
                    if self._settings.smtp_user:
                        server.login(self._settings.smtp_user, smtp_password)
                    server.send_message(message)
            else:
                # STARTTLS (port 587) or plain
                with smtplib.SMTP(
                    self._settings.smtp_host,
                    self._settings.smtp_port,
                ) as server:
                    if self._settings.smtp_starttls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    if self._settings.smtp_user:
                        server.login(self._settings.smtp_user, smtp_password)
                    server.send_message(message)

            logger.info("Email sent to %s", to_email)

        except Exception as e:
            logger.error("Failed to send email to %s: %s", to_email, e)
            raise

    def send_password_reset_email(self, to_email: str, reset_link: str) -> None:
        if not self._settings.smtp_enabled:
            logger.warning(
                "SMTP disabled, skipping password reset email to %s (link: %s)",
                to_email,
                reset_link,
            )
            return

        text_body = PASSWORD_RESET_TEXT.format(reset_link=reset_link)
        html_body = PASSWORD_RESET_HTML.format(reset_link=reset_link)

        message = self._create_message(
            to_email=to_email,
            subject=PASSWORD_RESET_SUBJECT,
            text_body=text_body,
            html_body=html_body,
        )

        self._send_email(to_email, message)
