"""Transactional email - EmailJS REST API, falling back to SMTP.

EmailJS is used whenever EMAILJS_SERVICE_ID is set (see config.py for the
full credential list and the exact dashboard steps, including the
"Allow non-browser requests" toggle that server-to-server calls need).
Otherwise this falls back to the SMTP path (SMTP_* in config.py), so an
existing SMTP setup keeps working with no config changes.

Both paths share the same send_email(to, subject, html, text) contract, and
callers like send_password_reset_email()/send_otp_email() don't need to
know which one is active.

Requires SMTP_USERNAME + SMTP_PASSWORD for the SMTP path, or
EMAILJS_SERVICE_ID/TEMPLATE_ID/PUBLIC_KEY for the EmailJS path. If neither
is configured, send_email logs a warning and returns False instead of
raising - callers should treat email delivery as best-effort and never let
it block the underlying action (e.g. password reset token creation must
still succeed even if the email fails to send).

A note on inbox placement: authenticating as a personal mailbox (Gmail
with an App Password) sends to any recipient with no domain verification,
but the brand in the From display name has no DKIM relationship with the
sending domain, so filters reasonably treat it as suspicious. EmailJS
routes through its connected service's own sending infrastructure, which
is generally a step up; a provider with a verified sender/domain is still
the real fix for spam-foldering.
"""
import logging
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate, make_msgid

import requests

import config

logger = logging.getLogger(__name__)

EMAILJS_API_URL = "https://api.emailjs.com/api/v1.0/email/send"


def _html_to_text(html: str) -> str:
    """Naive fallback for callers that don't supply their own plain-text
    version - strips tags and collapses whitespace. Good enough as a safety
    net; callers with real content should pass `text` explicitly instead."""
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _send_via_emailjs(to: str, subject: str, html: str, text: str, template_id: str, extra_params: dict = None) -> bool:
    """POST to EmailJS's send endpoint.

    EmailJS has no fixed variable-naming convention - it's whatever the
    template author typed into the template editor - and every template
    we've hit so far (a pre-built OTP template, EmailJS's own "Password
    Reset" starter) has used different names for the same two things: the
    recipient and the link. Rather than force the template to match our
    naming (or vice versa) every time a template changes, we send both
    common spellings for each: to_email/email for the recipient,
    reset_link/link for the link. Costs nothing - a template only reads the
    variables it references and ignores the rest - and means a stock
    EmailJS template mostly works with zero edits.
    """
    template_params = {
        "to_email": to,
        "email": to,
        "subject": subject,
        "html_body": html,
        "text_body": text,
    }
    if extra_params:
        template_params.update(extra_params)
        if "reset_link" in extra_params:
            template_params["link"] = extra_params["reset_link"]

    payload = {
        "service_id": config.EMAILJS_SERVICE_ID,
        "template_id": template_id,
        "user_id": config.EMAILJS_PUBLIC_KEY,
        "template_params": template_params,
    }
    if config.EMAILJS_PRIVATE_KEY:
        payload["accessToken"] = config.EMAILJS_PRIVATE_KEY

    try:
        response = requests.post(EMAILJS_API_URL, json=payload, timeout=15)
        if response.status_code >= 400:
            logger.error("EmailJS API error %s: %s", response.status_code, response.text[:300])
            return False
        logger.info("EmailJS accepted message for delivery to %s", to)
        return True
    except requests.exceptions.RequestException as exc:
        logger.error("Failed to send email via EmailJS: %s", exc)
        return False


def _send_via_smtp(to: str, subject: str, html: str, text: str) -> bool:
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
    msg.attach(MIMEText(text, "plain"))
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


def send_email(
    to: str, subject: str, html: str, text: str = None,
    extra_params: dict = None, emailjs_template_id: str = None,
) -> bool:
    """Send a transactional email. Returns True on success, False otherwise.

    Routes to EmailJS if configured, otherwise SMTP (extra_params and
    emailjs_template_id are EmailJS-only - the SMTP path ignores them).
    emailjs_template_id lets different email types use different EmailJS
    templates (see EMAILJS_TEMPLATE_ID_OTP/_RESET in config.py); it defaults
    to EMAILJS_TEMPLATE_ID when not given. Always sends a text/plain
    alternative alongside the HTML - an HTML-only message is one of the
    more heavily-weighted signals in spam scoring (SpamAssassin's
    MIME_HTML_ONLY rule and similar).
    """
    text = text or _html_to_text(html)

    if config.EMAILJS_SERVICE_ID:
        return _send_via_emailjs(
            to, subject, html, text,
            template_id=emailjs_template_id or config.EMAILJS_TEMPLATE_ID,
            extra_params=extra_params,
        )

    if not config.SMTP_USERNAME or not config.SMTP_PASSWORD:
        logger.warning(
            "Neither EMAILJS_SERVICE_ID nor SMTP_USERNAME/SMTP_PASSWORD is set - "
            "skipping email send to %s", to
        )
        return False

    return _send_via_smtp(to, subject, html, text)


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
    return send_email(
        to, "Reset your Pragna-1 A password", html, text=text,
        extra_params={"reset_link": reset_url},
        emailjs_template_id=config.EMAILJS_TEMPLATE_ID_RESET,
    )


def send_otp_email(to: str, code: str, ttl_minutes: int = 10) -> bool:
    """Send a signup-verification OTP code.

    Sends passcode/time in addition to the standard alias set, matching the
    variable names EmailJS's own "One-Time Password" starter template uses
    ({{passcode}}, {{time}}) - see the module docstring on variable-naming.
    """
    html = f"""
    <div style="font-family: -apple-system, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #1a1a1a;">Verify your Pragna-1 A account</h2>
      <p style="color: #444; line-height: 1.6;">
        Use the code below to finish creating your account. It expires in {ttl_minutes} minutes.
      </p>
      <p style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #d4af37; margin: 28px 0;">
        {code}
      </p>
      <p style="color: #888; font-size: 13px; line-height: 1.6;">
        If you didn't request this, you can safely ignore this email.
      </p>
    </div>
    """
    text = (
        f"Verify your Pragna-1 A account\n\n"
        f"Your verification code is: {code}\n\n"
        f"It expires in {ttl_minutes} minutes. If you didn't request this, ignore this email."
    )
    return send_email(
        to, "Your Pragna-1 A verification code", html, text=text,
        extra_params={"passcode": code, "time": f"{ttl_minutes} minutes"},
        emailjs_template_id=config.EMAILJS_TEMPLATE_ID_OTP,
    )
