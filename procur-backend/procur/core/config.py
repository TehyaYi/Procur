from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "Procur"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    
    # Security
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str] = ["*"]
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "https://procur.app"]
    
    # React Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    CDN_URL: Optional[str] = None
    
    # Firebase
    FIREBASE_CREDENTIALS_PATH: str
    FIREBASE_PROJECT_ID: str
    
    # Database
    DATABASE_URL: Optional[str] = None
    
    # Email
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM_EMAIL: str
    
    # Redis (for caching)
    REDIS_URL: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # File uploads
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # WebSocket (for real-time features)
    ENABLE_WEBSOCKETS: bool = True
    
    # Feature flags
    ENABLE_RATE_LIMITING: bool = True
    ENABLE_EMAIL_NOTIFICATIONS: bool = True
    ENABLE_FILE_UPLOADS: bool = True
    ENABLE_REAL_TIME_NOTIFICATIONS: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()
