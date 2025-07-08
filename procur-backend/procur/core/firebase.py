import firebase_admin
from firebase_admin import credentials, firestore, auth
from procur.core.config import get_settings
import logging
import os

logger = logging.getLogger(__name__)

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

def verify_firebase_token(token: str) -> dict:
    """Verify Firebase ID token"""
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise

# EOF