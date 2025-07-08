from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import logging
import os
from procur.core.config import get_settings
from procur.core.firebase import initialize_firebase
from procur.core.middleware import RateLimitMiddleware, LoggingMiddleware
from procur.core.exceptions import (
    procur_exception_handler,
    validation_exception_handler,
    http_exception_handler,
    general_exception_handler,
    ProcurException
)
from procur.api.routes import auth, groups, users, invitations, uploads
from procur.core.logging import setup_logging
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import ValidationError
from procur.core.startup import init_services

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("🚀 DEBUG: Starting application lifespan...")
    logger.info("Starting Procur application...")
    
    # Initialize Firebase
    try:
        print("🚀 DEBUG: About to initialize Firebase...")
        initialize_firebase()
        print("🚀 DEBUG: Firebase initialization completed")
        logger.info("Firebase initialized successfully")
    except Exception as e:
        print(f"🚀 DEBUG: Firebase initialization failed: {e}")
        logger.error(f"Failed to initialize Firebase: {e}")
        raise
    
    # Create upload directories
    os.makedirs("uploads/groups", exist_ok=True)
    os.makedirs("uploads/users", exist_ok=True)
    print("🚀 DEBUG: Upload directories created")
    
    yield
    
    print("🚀 DEBUG: Shutting down application...")
    logger.info("Shutting down Procur application...")

# Initialize FastAPI app
app = FastAPI(
    title="Procur GPO Platform API",
    description="Group Purchasing Organization platform for vertical-specific buying groups",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan  # ← Make sure this is here
)

settings = get_settings()

# Security middleware
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# Enhanced CORS for React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS + ["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time", "X-RateLimit-Remaining"],
)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware)

# Exception handlers
app.add_exception_handler(ProcurException, procur_exception_handler)
app.add_exception_handler(ValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(groups.router, prefix="/api/groups", tags=["Groups"])
app.include_router(invitations.router, prefix="/api/invitations", tags=["Invitations"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["File Uploads"])

# Serve uploaded files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Serve React app (for production)
if settings.ENVIRONMENT == "production" and os.path.exists("build"):
    app.mount("/static", StaticFiles(directory="build/static"), name="static")
    
    @app.get("/{path:path}")
    async def serve_react_app(path: str):
        """Serve React app for client-side routing"""
        if path.startswith("api/"):
            return {"error": "API endpoint not found"}
        
        file_path = f"build/{path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # Return index.html for client-side routing
        return FileResponse("build/index.html")

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "message": "Procur GPO Platform API",
        "version": "1.0.0",
        "frontend": "React",
        "docs": "/api/docs"
    }

@app.get("/api")
async def api_root():
    """API information endpoint for React app"""
    return {
        "name": "Procur API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth",
            "users": "/api/users", 
            "groups": "/api/groups",
            "invitations": "/api/invitations",
            "uploads": "/api/uploads"
        },
        "docs": "/api/docs"
    }

@app.get("/health")
async def health_check():
    """Enhanced health check for React app"""
    import time
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
        "services": {
            "firebase": "connected",
            "api": "running"
        }
    }

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    print("🚀 DEBUG: Starting application lifespan...")
    logger.info("Starting Procur application...")
    
    # Initialize Firebase
    try:
        print("🚀 DEBUG: About to initialize Firebase...")
        initialize_firebase()
        print("🚀 DEBUG: Firebase initialization completed")
        logger.info("Firebase initialized successfully")
    except Exception as e:
        print(f"🚀 DEBUG: Firebase initialization failed: {e}")
        logger.error(f"Failed to initialize Firebase: {e}")
        raise
    
    # Create upload directories
    os.makedirs("uploads/groups", exist_ok=True)
    os.makedirs("uploads/users", exist_ok=True)
    print("🚀 DEBUG: Upload directories created")
    
    yield
    
    print("🚀 DEBUG: Shutting down application...")
    logger.info("Shutting down Procur application...")
