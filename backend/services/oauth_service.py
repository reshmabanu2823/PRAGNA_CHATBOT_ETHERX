"""Google/GitHub OAuth2 login - standard authorization-code flow.

CSRF protection uses a signed, time-limited `state` token (itsdangerous)
instead of a server-side session, consistent with the rest of this app's
stateless-JWT auth model: nothing to store or clean up, and it survives a
gunicorn worker restart between the /login and /callback legs of the
redirect round trip (a server-side session dict wouldn't, if the callback
lands on a different worker).
"""
import logging
import re
import secrets
from urllib.parse import urlencode

import requests
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import config

logger = logging.getLogger(__name__)

STATE_MAX_AGE_SECONDS = 600  # 10 minutes is plenty for a login redirect round trip
_serializer = URLSafeTimedSerializer(config.JWT_SECRET, salt='oauth-state')


def make_state():
    """A random nonce, signed so /callback can trust it wasn't forged - it
    embeds no data, just proves this request round-tripped through our own
    /login redirect rather than being a CSRF'd callback hit directly."""
    return _serializer.dumps(secrets.token_urlsafe(16))


def verify_state(state):
    """True if `state` is a token we signed within the last
    STATE_MAX_AGE_SECONDS, False if it's missing, tampered, or expired."""
    if not state:
        return False
    try:
        _serializer.loads(state, max_age=STATE_MAX_AGE_SECONDS)
        return True
    except (BadSignature, SignatureExpired):
        return False


def sanitize_username(raw):
    """Turn a display name / email-local-part into a DB-safe username seed.
    Collision resolution (appending a numeric suffix) happens in
    database.py's create_oauth_user, not here."""
    base = re.sub(r'[^a-zA-Z0-9_]', '', (raw or '').strip().replace(' ', '_')).lower()
    return base[:30] or 'user'


# ── Google ───────────────────────────────────────────────────────────────

GOOGLE_AUTHORIZE_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'


def google_authorize_url(redirect_uri, state):
    params = {
        'client_id': config.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'access_type': 'online',
        'prompt': 'select_account',
    }
    return f"{GOOGLE_AUTHORIZE_URL}?{urlencode(params)}"


def google_fetch_profile(code, redirect_uri):
    """Exchange an auth code for a profile. Returns
    {'email', 'username_hint', 'oauth_id'}, or raises RuntimeError with a
    message safe to log (callers decide what, if anything, reaches the user)."""
    token_res = requests.post(GOOGLE_TOKEN_URL, data={
        'code': code,
        'client_id': config.GOOGLE_CLIENT_ID,
        'client_secret': config.GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }, timeout=10)
    if token_res.status_code >= 400:
        raise RuntimeError(f"Google token exchange failed ({token_res.status_code}): {token_res.text[:300]}")

    access_token = token_res.json().get('access_token')
    if not access_token:
        raise RuntimeError('Google token response missing access_token')

    profile_res = requests.get(
        GOOGLE_USERINFO_URL,
        headers={'Authorization': f'Bearer {access_token}'},
        timeout=10,
    )
    if profile_res.status_code >= 400:
        raise RuntimeError(f"Google userinfo fetch failed ({profile_res.status_code}): {profile_res.text[:300]}")
    profile = profile_res.json()

    email = profile.get('email')
    if not email:
        raise RuntimeError('Google account has no email on file')
    if profile.get('email_verified') is False:
        raise RuntimeError('Google email is not verified')

    oauth_id = profile.get('sub')
    if not oauth_id:
        raise RuntimeError('Google profile response missing sub (user id)')

    return {
        'email': email,
        'username_hint': sanitize_username(email.split('@')[0]),
        'oauth_id': oauth_id,
    }


# ── GitHub ───────────────────────────────────────────────────────────────

GITHUB_AUTHORIZE_URL = 'https://github.com/login/oauth/authorize'
GITHUB_TOKEN_URL = 'https://github.com/login/oauth/access_token'
GITHUB_USER_URL = 'https://api.github.com/user'
GITHUB_EMAILS_URL = 'https://api.github.com/user/emails'


def github_authorize_url(redirect_uri, state):
    params = {
        'client_id': config.GITHUB_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'scope': 'read:user user:email',
        'state': state,
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


def github_fetch_profile(code, redirect_uri):
    """Exchange an auth code for a profile. Returns
    {'email', 'username_hint', 'oauth_id'}, or raises RuntimeError."""
    token_res = requests.post(
        GITHUB_TOKEN_URL,
        data={
            'client_id': config.GITHUB_CLIENT_ID,
            'client_secret': config.GITHUB_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri,
        },
        headers={'Accept': 'application/json'},
        timeout=10,
    )
    if token_res.status_code >= 400:
        raise RuntimeError(f"GitHub token exchange failed ({token_res.status_code}): {token_res.text[:300]}")

    token_data = token_res.json()
    access_token = token_data.get('access_token')
    if not access_token:
        raise RuntimeError(f"GitHub token response missing access_token: {token_data.get('error_description', token_data)}")

    headers = {'Authorization': f'Bearer {access_token}', 'Accept': 'application/vnd.github+json'}
    user_res = requests.get(GITHUB_USER_URL, headers=headers, timeout=10)
    if user_res.status_code >= 400:
        raise RuntimeError(f"GitHub user fetch failed ({user_res.status_code}): {user_res.text[:300]}")
    user = user_res.json()

    # GitHub omits `email` from /user when the primary address is set to
    # private - the user:email scope grants the dedicated endpoint instead.
    email = user.get('email')
    if not email:
        emails_res = requests.get(GITHUB_EMAILS_URL, headers=headers, timeout=10)
        if emails_res.status_code < 400:
            entries = emails_res.json()
            primary = next((e['email'] for e in entries if e.get('primary') and e.get('verified')), None)
            any_verified = next((e['email'] for e in entries if e.get('verified')), None)
            email = primary or any_verified

    if not email:
        raise RuntimeError('GitHub account has no verified email available - add/verify one at github.com/settings/emails')

    oauth_id = user.get('id')
    if oauth_id is None:
        raise RuntimeError('GitHub profile response missing id')

    return {
        'email': email,
        'username_hint': sanitize_username(user.get('login') or email.split('@')[0]),
        'oauth_id': str(oauth_id),
    }
