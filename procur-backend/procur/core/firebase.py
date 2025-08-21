import firebase_admin
from firebase_admin import credentials, firestore, auth
from procur.core.config import get_settings
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
import time

logger = logging.getLogger(__name__)

# In-memory token blacklist (in production, use Redis or database)
_token_blacklist: Dict[str, float] = {}
_rate_limit_attempts: Dict[str, list] = {}

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    print("🔥 DEBUG: Starting Firebase initialization...")
    
    try:
        settings = get_settings()
        print(f"🔥 DEBUG: Firebase credentials path: {settings.FIREBASE_CREDENTIALS_PATH}")
        print(f"🔥 DEBUG: Firebase project ID: {settings.FIREBASE_PROJECT_ID}")
        
        # Check if file exists
        if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
            raise FileNotFoundError(f"Firebase credentials file not found: {settings.FIREBASE_CREDENTIALS_PATH}")
        
        # Check if file is readable
        with open(settings.FIREBASE_CREDENTIALS_PATH, 'r') as f:
            import json
            cred_data = json.load(f)
            print(f"🔥 DEBUG: Credentials file loaded, project_id in file: {cred_data.get('project_id')}")
    
        if not firebase_admin._apps:
            print("🔥 DEBUG: No existing Firebase apps, initializing...")
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred, {
                'projectId': settings.FIREBASE_PROJECT_ID,
            })
            print("🔥 DEBUG: Firebase app initialized successfully")
            logger.info("Firebase Admin SDK initialized successfully")
        else:
            print("🔥 DEBUG: Firebase app already exists")
            
    except Exception as e:
        print(f"🔥 DEBUG: Firebase initialization error: {e}")
        logger.error(f"Failed to initialize Firebase: {e}")
        raise

def get_firestore_client():
    """Get Firestore client"""
    print("🔥 DEBUG: Getting Firestore client...")
    if not firebase_admin._apps:
        print("🔥 DEBUG: No Firebase apps found!")
        raise ValueError("Firebase not initialized. Call initialize_firebase() first.")
    
    print("🔥 DEBUG: Firebase apps found, returning client")
    return firestore.client()

def _check_rate_limit(identifier: str, max_attempts: int = 5, window_seconds: int = 60) -> bool:
    """Check rate limiting for authentication attempts"""
    current_time = time.time()
    
    # Clean old attempts
    if identifier in _rate_limit_attempts:
        _rate_limit_attempts[identifier] = [
            attempt_time for attempt_time in _rate_limit_attempts[identifier]
            if current_time - attempt_time < window_seconds
        ]
    else:
        _rate_limit_attempts[identifier] = []
    
    # Check if limit exceeded
    if len(_rate_limit_attempts[identifier]) >= max_attempts:
        return False
    
    # Add current attempt
    _rate_limit_attempts[identifier].append(current_time)
    return True

def _is_token_blacklisted(token: str) -> bool:
    """Check if token is blacklisted"""
    if token in _token_blacklist:
        # Clean expired blacklist entries
        current_time = time.time()
        if current_time > _token_blacklist[token]:
            del _token_blacklist[token]
            return False
        return True
    return False

def blacklist_token(token: str, expires_in_seconds: int = 3600) -> None:
    """Add token to blacklist (e.g., after logout)"""
    _token_blacklist[token] = time.time() + expires_in_seconds
    logger.info(f"Token blacklisted for user, expires in {expires_in_seconds} seconds")

def verify_firebase_token(token: str, check_rate_limit: bool = True) -> dict:
    """Verify Firebase ID token with enhanced security"""
    try:
        # Check if token is blacklisted
        if _is_token_blacklisted(token):
            logger.warning("Attempted to use blacklisted token")
            raise ValueError("Token has been revoked")
        
        # Rate limiting check (optional, can be disabled for internal calls)
        if check_rate_limit:
            # Use first 8 characters of token as identifier for rate limiting
            token_id = token[:8]
            if not _check_rate_limit(token_id):
                logger.warning(f"Rate limit exceeded for token {token_id}")
                raise ValueError("Too many authentication attempts. Please try again later.")
        
        # Verify the token with Firebase
        decoded_token = auth.verify_id_token(token)
        
        # Additional security checks
        current_time = datetime.utcnow().timestamp()
        
        # Check if token is expired
        if 'exp' in decoded_token and decoded_token['exp'] < current_time:
            logger.warning("Attempted to use expired token")
            raise ValueError("Token has expired")
        
        # Check if token was issued too long ago (optional security measure)
        if 'iat' in decoded_token:
            issued_time = decoded_token['iat']
            max_age = 24 * 60 * 60  # 24 hours
            if current_time - issued_time > max_age:
                logger.warning("Token is too old")
                raise ValueError("Token is too old. Please re-authenticate.")
        
        # Check if user is disabled (if available in token claims)
        if decoded_token.get('disabled', False):
            logger.warning("Attempted to use token for disabled user")
            raise ValueError("User account is disabled")
        
        # Log successful authentication
        logger.info(f"Successful token verification for user {decoded_token.get('uid', 'unknown')}")
        
        return decoded_token
        
    except ValueError as e:
        logger.warning(f"Token validation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise ValueError("Invalid authentication token")

def revoke_user_tokens(uid: str) -> None:
    """Revoke all tokens for a specific user (e.g., after password change)"""
    try:
        auth.revoke_refresh_tokens(uid)
        logger.info(f"All refresh tokens revoked for user {uid}")
    except Exception as e:
        logger.error(f"Failed to revoke tokens for user {uid}: {e}")
        raise

def get_user_info(uid: str) -> Optional[dict]:
    """Get user information from Firebase Auth"""
    try:
        user_record = auth.get_user(uid)
        return {
            'uid': user_record.uid,
            'email': user_record.email,
            'email_verified': user_record.email_verified,
            'display_name': user_record.display_name,
            'disabled': user_record.disabled,
            'created_at': user_record.user_metadata.creation_timestamp,
            'last_sign_in': user_record.user_metadata.last_sign_in_timestamp
        }
    except Exception as e:
        logger.error(f"Failed to get user info for {uid}: {e}")
        return None

def update_user_claims(uid: str, custom_claims: dict) -> None:
    """Update custom claims for a user"""
    try:
        auth.set_custom_user_claims(uid, custom_claims)
        logger.info(f"Updated custom claims for user {uid}")
    except Exception as e:
        logger.error(f"Failed to update claims for user {uid}: {e}")
        raise

def create_user_with_email(email: str, password: str, display_name: str = None) -> auth.UserRecord:
    """Create a new user with email and password"""
    try:
        user_properties = {
            'email': email,
            'password': password,
            'email_verified': False,
        }
        
        if display_name:
            user_properties['display_name'] = display_name
            
        user_record = auth.create_user(**user_properties)
        logger.info(f"Created new user: {user_record.uid}")
        return user_record
        
    except Exception as e:
        logger.error(f"Failed to create user with email {email}: {e}")
        raise

def sign_in_with_email(email: str, password: str) -> auth.UserRecord:
    """Sign in user with email and password (simulated)"""
    try:
        # In Firebase Admin SDK, we can't directly sign in with email/password
        # Instead, we'll get the user by email and verify they exist
        user_record = auth.get_user_by_email(email)
        
        # Note: In a real implementation, you'd need to use Firebase Auth REST API
        # or Firebase Auth client SDK for actual password verification
        # For now, we'll assume the user exists and is valid
        
        logger.info(f"User signed in: {user_record.uid}")
        return user_record
        
    except Exception as e:
        logger.error(f"Failed to sign in user with email {email}: {e}")
        raise

def create_custom_token(uid: str) -> str:
    """Create a custom token for the user"""
    try:
        custom_token = auth.create_custom_token(uid)
        logger.info(f"Created custom token for user: {uid}")
        return custom_token.decode('utf-8')
        
    except Exception as e:
        logger.error(f"Failed to create custom token for user {uid}: {e}")
        raise

# EOF