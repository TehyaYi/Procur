from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger(__name__)

class ProcurException(Exception):
    """Base exception class for Procur application"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationException(ProcurException):
    """Validation error exception"""
    def __init__(self, message: str):
        super().__init__(message, 400)

class AuthenticationException(ProcurException):
    """Authentication error exception"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401)

class AuthorizationException(ProcurException):
    """Authorization error exception"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, 403)

class NotFoundException(ProcurException):
    """Resource not found exception"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)

class ConflictException(ProcurException):
    """Resource conflict exception"""
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, 409)

# Exception handlers
async def procur_exception_handler(request: Request, exc: ProcurException):
    """Handle custom Procur exceptions"""
    logger.error(f"ProcurException: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.message,
            "error_type": exc.__class__.__name__
        }
    )

async def validation_exception_handler(request: Request, exc: Exception):
    """Handle validation exceptions"""
    logger.error(f"Validation error: {str(exc)}")
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "message": "Validation error",
            "errors": [str(exc)]
        }
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP error {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error"
        }
    )
