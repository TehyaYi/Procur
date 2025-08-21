"""
Security Configuration for Procur GPO Platform
This module contains security-related configuration and best practices.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
import os

class SecurityConfig(BaseModel):
    """Security configuration settings"""
    
    # Authentication
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Security
    MIN_PASSWORD_LENGTH: int = 8
    REQUIRE_UPPERCASE: bool = True
    REQUIRE_LOWERCASE: bool = True
    REQUIRE_DIGITS: bool = True
    REQUIRE_SPECIAL_CHARS: bool = True
    PASSWORD_HISTORY_COUNT: int = 5
    
    # Session Security
    SESSION_TIMEOUT_MINUTES: int = 60
    MAX_CONCURRENT_SESSIONS: int = 5
    SESSION_INACTIVITY_TIMEOUT: int = 30
    
    # Rate Limiting
    AUTH_RATE_LIMIT: int = 5  # attempts per window
    AUTH_RATE_LIMIT_WINDOW: int = 300  # seconds (5 minutes)
    API_RATE_LIMIT: int = 100  # requests per window
    API_RATE_LIMIT_WINDOW: int = 60  # seconds (1 minute)
    
    # File Upload Security
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_EXTENSIONS: List[str] = [
        ".jpg", ".jpeg", ".png", ".gif", ".webp",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx",
        ".txt", ".csv"
    ]
    BLOCKED_FILE_EXTENSIONS: List[str] = [
        ".exe", ".bat", ".cmd", ".com", ".pif",
        ".scr", ".vbs", ".js", ".jar", ".war",
        ".ear", ".apk", ".ipa", ".dmg", ".deb",
        ".rpm", ".msi", ".app", ".sh", ".ps1"
    ]
    
    # CORS Security
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://procur.app",
        "https://www.procur.app"
    ]
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = [
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-API-Key"
    ]
    
    # Security Headers
    SECURITY_HEADERS: Dict[str, str] = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }
    
    # Content Security Policy
    CSP_POLICY: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.gstatic.com https://www.googleapis.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https://identitytoolkit.googleapis.com https://securetoken.googleapis.com; "
        "frame-src 'self' https://www.google.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # Firebase Security
    FIREBASE_TOKEN_EXPIRY: int = 3600  # 1 hour
    FIREBASE_REFRESH_TOKEN_EXPIRY: int = 604800  # 7 days
    FIREBASE_MAX_TOKEN_AGE: int = 86400  # 24 hours
    
    # Audit Logging
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_LEVEL: str = "INFO"
    AUDIT_LOG_RETENTION_DAYS: int = 90
    
    # Encryption
    ENCRYPTION_ALGORITHM: str = "AES-256-GCM"
    KEY_DERIVATION_ITERATIONS: int = 100000
    
    # API Security
    API_KEY_HEADER: str = "X-API-Key"
    API_KEY_REQUIRED: bool = False
    API_VERSION_HEADER: str = "X-API-Version"
    API_VERSION_REQUIRED: bool = True
    
    # Database Security
    DB_CONNECTION_ENCRYPTION: bool = True
    DB_QUERY_TIMEOUT: int = 30
    DB_MAX_CONNECTIONS: int = 20
    
    # Monitoring and Alerting
    SECURITY_MONITORING_ENABLED: bool = True
    FAILED_LOGIN_ALERT_THRESHOLD: int = 10
    SUSPICIOUS_ACTIVITY_ALERT_THRESHOLD: int = 5
    
    # Backup and Recovery
    BACKUP_ENCRYPTION_ENABLED: bool = True
    BACKUP_RETENTION_DAYS: int = 30
    DISASTER_RECOVERY_ENABLED: bool = True

# Security best practices
SECURITY_BEST_PRACTICES = {
    "authentication": [
        "Use strong password policies",
        "Implement multi-factor authentication",
        "Use secure session management",
        "Implement account lockout policies",
        "Regular password rotation"
    ],
    "authorization": [
        "Principle of least privilege",
        "Role-based access control",
        "Regular permission reviews",
        "Separation of duties",
        "Access logging and monitoring"
    ],
    "data_protection": [
        "Encrypt data at rest and in transit",
        "Implement data classification",
        "Regular data backups",
        "Secure data disposal",
        "Data loss prevention"
    ],
    "network_security": [
        "Use HTTPS for all communications",
        "Implement network segmentation",
        "Regular security updates",
        "Intrusion detection systems",
        "Firewall configuration"
    ],
    "application_security": [
        "Input validation and sanitization",
        "Output encoding",
        "Secure error handling",
        "Regular security testing",
        "Dependency vulnerability scanning"
    ]
}

# Security checklist for production deployment
PRODUCTION_SECURITY_CHECKLIST = [
    "Change default passwords and API keys",
    "Enable HTTPS with valid SSL certificates",
    "Configure proper CORS policies",
    "Enable security headers",
    "Implement rate limiting",
    "Enable audit logging",
    "Configure backup and recovery",
    "Set up monitoring and alerting",
    "Perform security testing",
    "Document security procedures",
    "Train team on security practices",
    "Establish incident response plan"
]

def get_security_config() -> SecurityConfig:
    """Get security configuration"""
    return SecurityConfig()

def validate_security_settings() -> Dict[str, List[str]]:
    """Validate security settings and return any issues"""
    config = get_security_config()
    issues = []
    warnings = []
    
    # Check for weak passwords
    if config.MIN_PASSWORD_LENGTH < 8:
        issues.append("Minimum password length should be at least 8 characters")
    
    # Check for weak JWT secret
    if config.JWT_SECRET_KEY == "your-secret-key-change-in-production":
        issues.append("JWT secret key must be changed from default value")
    
    # Check for overly permissive CORS
    if "*" in config.ALLOWED_ORIGINS:
        warnings.append("CORS allows all origins - consider restricting in production")
    
    # Check for weak encryption
    if config.KEY_DERIVATION_ITERATIONS < 100000:
        warnings.append("Key derivation iterations should be at least 100,000")
    
    return {
        "issues": issues,
        "warnings": warnings
    }

def get_security_headers() -> Dict[str, str]:
    """Get security headers configuration"""
    config = get_security_config()
    headers = config.SECURITY_HEADERS.copy()
    headers["Content-Security-Policy"] = config.CSP_POLICY
    return headers

def is_production_ready() -> bool:
    """Check if security configuration is production-ready"""
    validation = validate_security_settings()
    return len(validation["issues"]) == 0
