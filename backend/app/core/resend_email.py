"""Production transactional authentication email delivery via Resend."""

import asyncio
from urllib.parse import quote

import httpx

from app.core.config import Settings


class ResendEmailDeliveryError(RuntimeError):
    """Raised when Resend cannot accept an authentication email."""


def _email_content(
    settings: Settings,
    purpose: str,
    token: str | None,
    lifetime_seconds: int,
) -> tuple[str, str, str]:
    if purpose == "email-verification":
        subject = "Verify your SandeshVani email address"
        action = "verify your email address"
        parameter = "verify_token"
    elif purpose == "password-reset":
        subject = "Reset your SandeshVani password"
        action = "reset your password"
        parameter = "reset_token"
    else:
        raise ValueError("Unsupported authentication email purpose")

    if not token:
        # Keep known/unknown-account responses equivalent without disclosing
        # account existence. No actionable link is sent for unknown accounts.
        return (
            subject,
            "If this address is associated with an account, follow the instructions "
            "previously sent to you. If you did not request this, you can ignore this email.",
            "<p>If this address is associated with an account, follow the instructions "
            "previously sent to you. If you did not request this, you can ignore this email.</p>",
        )

    link = f"{settings.frontend_base_url.rstrip('/')}/?{parameter}={quote(token, safe='')}"
    minutes = max(1, lifetime_seconds // 60)
    text = (
        f"Use this link to {action}:\n\n{link}\n\n"
        f"This link expires in approximately {minutes} minutes. "
        "If you did not request this, you can ignore this email."
    )
    html = (
        f"<p>Use the link below to {action}:</p>"
        f'<p><a href="{link}">Continue to SandeshVani</a></p>'
        f"<p>This link expires in approximately {minutes} minutes. "
        "If you did not request this, you can ignore this email.</p>"
    )
    return subject, text, html


async def deliver_resend_auth_email(
    settings: Settings,
    recipient: str,
    purpose: str,
    token: str | None,
    lifetime_seconds: int,
) -> None:
    """Send an authentication email using the Resend HTTP API."""
    if not (
        settings.resend_api_key.strip()
        and settings.auth_email_from.strip()
        and settings.frontend_base_url.startswith("https://")
    ):
        raise ResendEmailDeliveryError("Resend email configuration is incomplete")

    subject, text_body, html_body = _email_content(
        settings, purpose, token, lifetime_seconds
    )
    payload = {
        "from": settings.auth_email_from,
        "to": [recipient],
        "subject": subject,
        "text": text_body,
        "html": html_body,
    }
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        for attempt in range(2):
            try:
                response = await client.post(
                    "https://api.resend.com/emails",
                    json=payload,
                    headers=headers,
                )
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                response.raise_for_status()
                return
            except httpx.HTTPStatusError as exc:
                raise ResendEmailDeliveryError(
                    f"Resend rejected the email with HTTP {exc.response.status_code}"
                ) from exc
            except httpx.HTTPError as exc:
                if attempt == 0:
                    await asyncio.sleep(0.5)
                    continue
                raise ResendEmailDeliveryError("Resend request failed") from exc

    raise ResendEmailDeliveryError("Resend request failed after retry")
