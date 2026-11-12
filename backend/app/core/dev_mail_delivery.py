"""Local SMTP delivery for development authentication messages.

This transport is intentionally usable only when the exact local mail sink
configuration is enabled. Production email delivery is a separate provider
integration and must not reuse the development transport.
"""

import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import Settings


class LocalEmailDeliveryError(RuntimeError):
    """Raised when a local development email cannot be delivered."""


def _build_message(
    settings: Settings,
    recipient: str,
    purpose: str,
    token: str | None,
    lifetime_seconds: int,
) -> EmailMessage:
    if purpose == "email-verification":
        subject = "Verify your SandeshVani email address"
        action = "email verification"
    elif purpose == "password-reset":
        subject = "Reset your SandeshVani password"
        action = "password reset"
    else:
        raise ValueError(f"Unsupported local authentication email purpose: {purpose}")

    if token:
        body = (
            f"Your SandeshVani {action} token is:\n\n"
            f"{token}\n\n"
            f"This token expires in approximately {lifetime_seconds // 60} minutes.\n"
            "For local development only, this message was delivered to Mailpit."
        )
    else:
        body = (
            "If this address is eligible, instructions would be delivered. "
            "No action is required."
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.dev_mail_from
    message["To"] = recipient
    message.set_content(body)
    return message


def _send_message(settings: Settings, message: EmailMessage) -> None:
    with smtplib.SMTP(
        settings.dev_mail_smtp_host,
        settings.dev_mail_smtp_port,
        timeout=10,
    ) as smtp:
        if settings.dev_mail_smtp_starttls:
            smtp.starttls()
        if settings.dev_mail_smtp_username:
            smtp.login(
                settings.dev_mail_smtp_username,
                settings.dev_mail_smtp_password,
            )
        smtp.send_message(message)


async def deliver_local_auth_email(
    settings: Settings,
    recipient: str,
    purpose: str,
    token: str | None,
    lifetime_seconds: int,
) -> None:
    """Send an auth email through the configured local SMTP server."""
    if not settings.is_local_mail_sink_enabled:
        raise LocalEmailDeliveryError(
            "Local SMTP delivery requires the local development mail sink."
        )
    if not settings.dev_mail_smtp_host:
        return

    message = _build_message(
        settings=settings,
        recipient=recipient,
        purpose=purpose,
        token=token,
        lifetime_seconds=lifetime_seconds,
    )
    try:
        await asyncio.to_thread(_send_message, settings, message)
    except (OSError, smtplib.SMTPException) as exc:
        raise LocalEmailDeliveryError("Local SMTP delivery failed.") from exc
