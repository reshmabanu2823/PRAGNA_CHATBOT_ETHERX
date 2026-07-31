"""Transactional email over SMTP.

Provider-agnostic - see the SMTP_* block in config.py for host/port/
credential settings and a table of common providers. Switching from Gmail
to Brevo/SendGrid/Mailgun is an environment change, not a code change.

Requires SMTP_USERNAME + SMTP_PASSWORD. If either is unset, send_email
logs a warning and returns False instead of raising - callers should treat
email delivery as best-effort and never let it block the underlying action
(e.g. password reset token creation must still succeed even if the email
fails to send).

A note on inbox placement: authenticating as a personal mailbox (Gmail
with an App Password) sends to any recipient with no domain verification,
but the brand in the From display name has no DKIM relationship with the
sending domain, so filters reasonably treat it as suspicious. A provider
with a verified sender or verified domain signs the mail properly and is
the real fix for spam-foldering.
"""
import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

import config

logger = logging.getLogger(__name__)


def _html_to_text(html: str) -> str:
    """Naive fallback for callers that don't supply their own plain-text
    version - strips tags and collapses whitespace. Good enough as a safety
    net; callers with real content should pass `text` explicitly instead."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def send_email(to: str, subject: str, html: str, text: str = None) -> bool:
    """Send a transactional email. Returns True on success, False otherwise.

    Always attaches a text/plain part alongside the HTML - an HTML-only
    message is one of the more heavily-weighted signals in spam scoring
    (SpamAssassin's MIME_HTML_ONLY rule and similar), which matters a lot
    more here than it did on Resend since this is unauthenticated personal-
    account mail rather than a purpose-built sending domain.
    """
    if not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
        logger.warning("SMTP_USERNAME/SMTP_PASSWORD not set - skipping email send to %s", to)
        return False

    from_email = config.SMTP_FROM_EMAIL
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{config.SMTP_FROM_NAME} <{from_email}>"
    msg["To"] = to
    # sendmail() transmits exactly the headers we build here - unlike some
    # clients, nothing downstream fills these in for us. A message with no
    # Date and no Message-ID trips MISSING_DATE/MISSING_MID in SpamAssassin
    # and equivalents, which is free spam score we don't need to be paying.
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=from_email.split("@")[-1])
    msg["Reply-To"] = from_email
    # RFC 3834: marks this as machine-generated so well-behaved receivers
    # don't auto-reply to it and can classify it as transactional.
    msg["Auto-Submitted"] = "auto-generated"
    # Plain-text part must come first - clients render the last alternative
    # that they support, so HTML (the richer version) goes second.
    msg.attach(MIMEText(text or _html_to_text(html), "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        # Port 465 is implicit TLS (wrapped from the first byte); everything
        # else - in practice 587 - starts in cleartext and upgrades via
        # STARTTLS. Getting this backwards fails at connect, not at login,
        # so it's worth branching rather than assuming one provider's shape.
        if config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15)
        with server:
            if config.SMTP_PORT != 465:
                server.starttls()
            server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            server.sendmail(from_email, [to], msg.as_string())
        # Deliberately not phrased as "sent" - SMTP returning 250 here only
        # means the provider accepted the message for delivery. Hard
        # failures (no such mailbox, etc.) arrive asynchronously as a bounce
        # to SMTP_USERNAME seconds later and are invisible from in here.
        logger.info("%s accepted message for delivery to %s", config.SMTP_HOST, to)
        return True
    except smtplib.SMTPException as exc:
        logger.error("Failed to send email via %s: %s", config.SMTP_HOST, exc)
        return False
    except OSError as exc:
        logger.error("Failed to connect to %s:%s: %s", config.SMTP_HOST, config.SMTP_PORT, exc)
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
    text = (
        "Reset your Pragna-1 A password\n\n"
        "We received a request to reset your password. Use the link below to choose a new one. "
        "This link expires in 60 minutes and can only be used once.\n\n"
        f"{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email - your password won't be changed."
    )
    return send_email(to, "Reset your Pragna-1 A password", html, text=text)
