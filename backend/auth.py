import jwt
import config
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify
from database import db
import hashlib

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
        """
        user = db.get_user_by_email(email)
        if not user:
            return  # Deliberately silent - see docstring

        token = db.create_password_reset_token(user['id'])
        reset_url = f"{config.FRONTEND_URL}/reset-password?token={token}"

        from services.email_service import send_password_reset_email
        send_password_reset_email(user['email'], reset_url)

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
