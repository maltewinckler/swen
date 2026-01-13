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
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .button {{ display: inline-block; padding: 12px 24px; background: #2563eb; color: white; text-decoration: none; border-radius: 6px; }}
        .footer {{ margin-top: 30px; color: #6b7280; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>Password Reset Request</h2>
        <p>You requested a password reset for your SWEN account.</p>
        <p>Click the button below to reset your password. This link is valid for 1 hour.</p>
        <p style="margin: 30px 0;">
            <a href="{reset_link}" class="button">Reset Password</a>
        </p>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #6b7280;">{reset_link}</p>
        <div class="footer">
            <p>If you didn't request this, you can safely ignore this email.</p>
            <p>-- SWEN</p>
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
