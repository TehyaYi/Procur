from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
import logging
from typing import Dict, Optional
import redis
from procur.core.config import get_settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app, redis_client: Optional[redis.Redis] = None):
        super().__init__(app)
        self.settings = get_settings()
        self.redis_client = redis_client
        
        if self.settings.REDIS_URL and not self.redis_client:
            try:
                self.redis_client = redis.from_url(self.settings.REDIS_URL)
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
    
    async def dispatch(self, request: Request, call_next):
        if not self.settings.ENABLE_RATE_LIMITING or not self.redis_client:
            return await call_next(request)
        
        # Get client IP
        client_ip = request.client.host
        if "x-forwarded-for" in request.headers:
            client_ip = request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Create rate limit key
        window = self.settings.RATE_LIMIT_WINDOW
        limit = self.settings.RATE_LIMIT_REQUESTS
        key = f"rate_limit:{client_ip}:{int(time.time() // window)}"
        
        try:
            # Increment counter
            current = self.redis_client.incr(key)
            
            # Set expiration on first request
            if current == 1:
                self.redis_client.expire(key, window)
            
            # Check if limit exceeded
            if current > limit:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Try again later.",
                    headers={"Retry-After": str(window)}
                )
            
            # Add rate limit headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(max(0, limit - current))
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)
            
            return response
            
        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiting: {e}")
            # Continue without rate limiting if Redis fails
            return await call_next(request)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log response
            logger.info(
                f"Response: {response.status_code} - "
                f"{request.method} {request.url.path} - "
                f"{process_time:.4f}s"
            )
            
            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error: {str(e)} - "
                f"{request.method} {request.url.path} - "
                f"{process_time:.4f}s"
            )
            raise
