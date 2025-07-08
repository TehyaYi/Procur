import logging
import sys
from procur.core.config import get_settings

def setup_logging():
    """Setup application logging"""
    settings = get_settings()
    
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('procur.log') if settings.ENVIRONMENT == 'production' else logging.NullHandler()
        ]
    )
    
    # Set specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("procur").setLevel(getattr(logging, settings.LOG_LEVEL))
