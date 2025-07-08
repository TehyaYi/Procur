# procur/core/startup.py
from procur.core.firebase import initialize_firebase
import logging

logger = logging.getLogger(__name__)

def init_services():
    """Initialize all services"""
    print("🔧 Initializing services...")
    try:
        initialize_firebase()
        print("✅ Firebase initialized")
        return True
    except Exception as e:
        print(f"❌ Service initialization failed: {e}")
        logger.error(f"Service initialization failed: {e}")
        return False

# EOF