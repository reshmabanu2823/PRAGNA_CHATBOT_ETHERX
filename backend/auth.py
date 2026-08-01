import jwt
import config
import logging
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from database import db
import hashlib

logger = logging.getLogger(__name__)

class AuthService:
    @staticmethod
    def generate_token(user_id, expires_in=7):
        """Generate JWT token"""
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(days=expires_in),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, config.JWT_SECRET, algorithm='HS256')
    
    @staticmethod
    def verify_token(token):
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, config.JWT_SECRET, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def register(username, email, password):
        """Register new user"""
        if len(password) < 8:
            return None, "Password must be at least 8 characters"
        
        user_id = db.create_user(username, email, password)
        if not user_id:
            return None, "Username or email already exists"
        
        token = AuthService.generate_token(user_id)
        return user_id, token
    
    OTP_TTL_MINUTES = 10

    @staticmethod
    def request_registration_otp(username, email, password):
        """Validate a signup attempt and email a 6-digit code, staging the
        account behind verify_registration_otp rather than creating it
        immediately - mirrors request_password_reset's shape (validate/
        stage synchronously, dispatch the email on a background thread so
        the request doesn't block on the SMTP/EmailJS round-trip).

        Unlike request_password_reset, this can't stay silent on "already
        taken" - the client needs to know before showing an OTP-entry
        screen for an account that will never be created, and username/
        email availability isn't secret the way "is this address
        registered" is (it's shown live on most signup forms anyway).
        Returns an error string, or None on success.
        """
        if len(password) < 8:
            return "Password must be at least 8 characters"

        if db.get_user(username):
            return "Username or email already exists"
        if db.get_user_by_email(email):
            return "Username or email already exists"

        otp_code = f"{secrets.randbelow(1_000_000):06d}"
        db.create_pending_registration(username, email, password, otp_code, ttl_minutes=AuthService.OTP_TTL_MINUTES)

        from services.email_service import send_otp_email
        import threading
        threading.Thread(
            target=send_otp_email,
            args=(email, otp_code),
            kwargs={"ttl_minutes": AuthService.OTP_TTL_MINUTES},
            daemon=True,
        ).start()
        return None

    @staticmethod
    def verify_registration_otp(email, code):
        """Check the code and, if it matches, actually create the account.
        Returns (user_id, token_or_error, error) - error is None on success,
        matching login()'s return shape so routes can handle both the same way.
        """
        pending = db.get_pending_registration(email)
        if not pending:
            return None, None, "No pending signup found for this email - request a new code"

        if pending['attempts'] >= db.MAX_OTP_ATTEMPTS:
            db.delete_pending_registration(email)
            return None, None, "Too many incorrect attempts - request a new code"

        if pending['otp_code'] != code:
            db.increment_otp_attempts(email)
            return None, None, "Incorrect code"

        db.delete_pending_registration(email)
        user_id = db._insert_user(pending['username'], pending['email'], pending['password_hash'])
        if not user_id:
            # Someone else took the username/email in the window between
            # request-otp and verify-otp - rare, but has to be handled.
            return None, None, "Username or email already exists"

        token = AuthService.generate_token(user_id)
        return user_id, token, None

    @staticmethod
    def login(username, password):
        """Login user"""
        user = db.get_user(username)
        if not user:
            return None, None, "Invalid username or password"

        if not db.verify_password(user['password_hash'], password):
            return None, None, "Invalid username or password"

        token = AuthService.generate_token(user['id'])
        return user['id'], token, None

    @staticmethod
    def change_password(user_id, current_password, new_password):
        """Verify the current password, then set a new one. Returns error string or None."""
        if len(new_password) < 8:
            return "New password must be at least 8 characters"

        user = db.get_user_by_id(user_id)
        if not user:
            return "User not found"

        if not db.verify_password(user['password_hash'], current_password):
            return "Current password is incorrect"

        if not db.update_password(user_id, new_password):
            return "Failed to update password"

        return None

    @staticmethod
    def delete_account(user_id, password):
        """Verify password, then permanently delete the account. Returns error string or None."""
        user = db.get_user_by_id(user_id)
        if not user:
            return "User not found"

        if not db.verify_password(user['password_hash'], password):
            return "Password is incorrect"

        if not db.delete_user(user_id):
            return "Failed to delete account"

        return None

    @staticmethod
    def request_password_reset(email):
        """Generate a reset token and email it, if the address belongs to a
        real account. Always call this the same way regardless of outcome -
        callers should return an identical response either way so this
        endpoint can't be used to enumerate registered emails.

        The token is created synchronously (fast, local DB write) but the
        email is dispatched on a background thread - send_email makes an
        SMTP connection with a 15s timeout, and doing that inline made the
        /api/auth/forgot-password request (and the "Send reset link" button)
        block for however long that SMTP round-trip took. The token already
        exists by the time this returns, so the reset link works immediately
        even if the email itself is still in flight.
        """
        user = db.get_user_by_email(email)
        if not user:
            # Silent to the *client* (see docstring) but noisy server-side:
            # without this, an unregistered address and a successfully-sent
            # email look identical in the logs, which makes "I requested a
            # reset and got nothing" impossible to diagnose. Safe to log -
            # the logs aren't the attack surface the silence protects.
            logger.info("Password reset requested for unregistered email: %s", email)
            return

        token = db.create_password_reset_token(user['id'])
        reset_url = f"{config.FRONTEND_URL}/reset-password?token={token}"

        from services.email_service import send_password_reset_email
        import threading
        threading.Thread(
            target=send_password_reset_email,
            args=(user['email'], reset_url),
            daemon=True,
        ).start()

    @staticmethod
    def reset_password(token, new_password):
        """Validate a reset token and set the new password. Returns error string or None."""
        if len(new_password) < 8:
            return "New password must be at least 8 characters"

        token_row = db.get_valid_reset_token(token)
        if not token_row:
            return "This reset link is invalid or has expired"

        if not db.update_password(token_row['user_id'], new_password):
            return "Failed to update password"

        db.mark_reset_token_used(token)
        return None

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return jsonify({'error': 'Missing authentication token'}), 401
        
        payload = AuthService.verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        # Add user_id to request context
        request.user_id = payload['user_id']
        return f(*args, **kwargs)
    
    return decorated

auth_service = AuthService()
