"""Transactional email via Resend's HTTP API.

Requires RESEND_API_KEY (get one free at resend.com). If unset, send_email
logs a warning and returns False instead of raising - callers should treat
email delivery as best-effort and never let it block the underlying action
(e.g. password reset token creation must still succeed even if the email
fails to send).
"""
import logging
import requests

import config

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str) -> bool:
    """Send a transactional email. Returns True on success, False otherwise."""
    if not config.RESEND_API_KEY:
        logger.warning("RESEND_API_KEY not set - skipping email send to %s", to)
        return False

    try:
        response = requests.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {config.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": config.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            },
            timeout=15,
        )
        if response.status_code >= 400:
            logger.error("Resend API error %s: %s", response.status_code, response.text[:300])
            return False
        return True
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to send email via Resend: %s", exc)
        return False


def send_password_reset_email(to: str, reset_url: str) -> bool:
    """Send the password reset link email."""
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #1a1a1a;">Reset your Pragna-1 A password</h2>
      <p style="color: #444; line-height: 1.6;">
        We received a request to reset your password. Click the button below to choose a new one.
        This link expires in 60 minutes and can only be used once.
      </p>
      <p style="margin: 28px 0;">
        <a href="{reset_url}" style="background: #d4af37; color: #1a1405; padding: 12px 24px;
           border-radius: 8px; text-decoration: none; font-weight: 600; display: inline-block;">
          Reset Password
        </a>
      </p>
      <p style="color: #888; font-size: 13px; line-height: 1.6;">
        If you didn't request this, you can safely ignore this email - your password won't be changed.
      </p>
      <p style="color: #888; font-size: 12px; word-break: break-all;">
        Or copy this link: {reset_url}
      </p>
    </div>
    """
    return send_email(to, "Reset your Pragna-1 A password", html)
