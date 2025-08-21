from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from procur.core.config import get_settings
import time
import logging
from typing import Dict, List
import json

logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
_rate_limit_storage: Dict[str, List[float]] = {}

def setup_security_middleware(app: FastAPI) -> None:
    """Setup security middleware for the FastAPI application"""
    settings = get_settings()
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-API-Key",
            "X-Client-Version",
            "X-Client-Platform"
        ],
        expose_headers=[
            "X-Total-Count",
            "X-Page-Count",
            "X-Current-Page",
            "X-Per-Page"
        ]
    )
    
    # Trusted host middleware
    if settings.ALLOWED_HOSTS != ["*"]:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # Gzip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Security headers middleware
    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy
        csp_policy = (
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
        response.headers["Content-Security-Policy"] = csp_policy
        
        # Remove server information
        response.headers["Server"] = "Procur"
        
        return response
    
    # Rate limiting middleware
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        if settings.ENABLE_RATE_LIMITING:
            client_ip = request.client.host
            endpoint = request.url.path
            
            # Skip rate limiting for health checks and static files
            if endpoint in ["/health", "/docs", "/redoc", "/openapi.json"] or endpoint.startswith("/static/"):
                return await call_next(request)
            
            # Apply rate limiting
            if not _check_rate_limit(client_ip, endpoint):
                logger.warning(f"Rate limit exceeded for IP: {client_ip}, endpoint: {endpoint}")
                return Response(
                    content=json.dumps({
                        "error": "Rate limit exceeded",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": 60
                    }),
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"}
                )
        
        # Add request timing
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log slow requests
        if process_time > 1.0:  # Log requests taking more than 1 second
            logger.warning(f"Slow request: {request.method} {endpoint} took {process_time:.3f}s from IP: {client_ip}")
        
        return response

def _check_rate_limit(client_ip: str, endpoint: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
    """Check rate limiting for a specific client and endpoint"""
    current_time = time.time()
    key = f"{client_ip}:{endpoint}"
    
    # Clean old requests
    if key in _rate_limit_storage:
        _rate_limit_storage[key] = [
            req_time for req_time in _rate_limit_storage[key]
            if current_time - req_time < window_seconds
        ]
    else:
        _rate_limit_storage[key] = []
    
    # Check if limit exceeded
    if len(_rate_limit_storage[key]) >= max_requests:
        return False
    
    # Add current request
    _rate_limit_storage[key].append(current_time)
    return True

def cleanup_rate_limit_storage() -> None:
    """Clean up expired rate limit entries"""
    current_time = time.time()
    expired_keys = []
    
    for key, timestamps in _rate_limit_storage.items():
        # Remove entries older than 1 hour
        _rate_limit_storage[key] = [
            ts for ts in timestamps
            if current_time - ts < 3600
        ]
        
        # Remove empty entries
        if not _rate_limit_storage[key]:
            expired_keys.append(key)
    
    for key in expired_keys:
        del _rate_limit_storage[key]

# Scheduled cleanup (in production, use a proper task scheduler)
import asyncio
async def schedule_rate_limit_cleanup():
    """Schedule periodic cleanup of rate limit storage"""
    while True:
        await asyncio.sleep(3600)  # Clean up every hour
        cleanup_rate_limit_storage()
        logger.debug("Rate limit storage cleaned up")

def get_security_headers() -> Dict[str, str]:
    """Get standard security headers"""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }

def validate_api_key(api_key: str) -> bool:
    """Validate API key (implement your own logic)"""
    # In production, validate against database or environment
    settings = get_settings()
    return api_key == getattr(settings, 'API_KEY', None)

def sanitize_input(input_string: str) -> str:
    """Basic input sanitization"""
    import html
    return html.escape(input_string.strip())

def validate_file_upload(filename: str, content_type: str, file_size: int) -> tuple[bool, str]:
    """Validate file upload security"""
    settings = get_settings()
    
    # Check file size
    if file_size > settings.MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE} bytes"
    
    # Check file type
    if content_type not in settings.ALLOWED_FILE_TYPES:
        return False, f"File type {content_type} is not allowed"
    
    # Check filename for suspicious patterns
    suspicious_patterns = ['..', '//', '\\', 'script', 'javascript', 'vbscript']
    filename_lower = filename.lower()
    for pattern in suspicious_patterns:
        if pattern in filename_lower:
            return False, f"Filename contains suspicious pattern: {pattern}"
    
    return True, "File validation passed"
