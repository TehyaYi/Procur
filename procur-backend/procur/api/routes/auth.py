from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials
from procur.core.dependencies import get_current_user, logout_user
from procur.core.firebase import revoke_user_tokens, get_user_info, create_user_with_email, sign_in_with_email
from procur.models.schemas import UserResponse, LogoutResponse, LoginRequest, RegisterRequest, AuthResponse
from fastapi.security import HTTPBearer
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
security = HTTPBearer()

@router.post("/login", response_model=AuthResponse)
async def login(login_data: LoginRequest):
    """Login user with email and password"""
    try:
        # Sign in with Firebase
        user_record = sign_in_with_email(login_data.email, login_data.password)
        
        # Get user data from Firestore
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
        user_doc = db.collection('users').document(user_record.uid).get()
        
        if not user_doc.exists:
            # Create user document if it doesn't exist
            user_data = {
                'email': user_record.email,
                'display_name': user_record.display_name or login_data.email.split('@')[0],
                'created_at': user_record.user_metadata.creation_timestamp,
                'updated_at': user_record.user_metadata.creation_timestamp,
                'is_verified': user_record.email_verified,
                'is_active': True,
            }
            db.collection('users').document(user_record.uid).set(user_data)
        else:
            user_data = user_doc.to_dict()
        
        # Create custom token for the frontend
        from procur.core.firebase import create_custom_token
        custom_token = create_custom_token(user_record.uid)
        
        logger.info(f"User {user_record.uid} logged in successfully")
        
        return AuthResponse(
            user=UserResponse(uid=user_record.uid, **user_data),
            token=custom_token,
            refresh_token=custom_token  # For simplicity, using same token
        )
        
    except Exception as e:
        logger.error(f"Login error for {login_data.email}: {e}")
        if "INVALID_PASSWORD" in str(e) or "USER_NOT_FOUND" in str(e):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        elif "TOO_MANY_ATTEMPTS_TRY_LATER" in str(e):
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
        else:
            raise HTTPException(status_code=500, detail="Login failed")

@router.post("/register", response_model=AuthResponse)
async def register(register_data: RegisterRequest):
    """Register new user with email and password"""
    try:
        # Create user in Firebase
        user_record = create_user_with_email(
            register_data.email, 
            register_data.password,
            display_name=register_data.display_name
        )
        
        # Create user document in Firestore
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
        
        user_data = {
            'email': register_data.email,
            'display_name': register_data.display_name,
            'company_name': register_data.company_name,
            'job_title': register_data.job_title,
            'industry': register_data.industry,
            'location': register_data.location,
            'phone_number': register_data.phone_number,
            'created_at': user_record.user_metadata.creation_timestamp,
            'updated_at': user_record.user_metadata.creation_timestamp,
            'is_verified': False,
            'is_active': True,
        }
        
        db.collection('users').document(user_record.uid).set(user_data)
        
        # Create custom token for the frontend
        from procur.core.firebase import create_custom_token
        custom_token = create_custom_token(user_record.uid)
        
        logger.info(f"User {user_record.uid} registered successfully")
        
        return AuthResponse(
            user=UserResponse(uid=user_record.uid, **user_data),
            token=custom_token,
            refresh_token=custom_token  # For simplicity, using same token
        )
        
    except Exception as e:
        logger.error(f"Registration error for {register_data.email}: {e}")
        if "EMAIL_EXISTS" in str(e):
            raise HTTPException(status_code=400, detail="Email already exists")
        elif "WEAK_PASSWORD" in str(e):
            raise HTTPException(status_code=400, detail="Password is too weak")
        else:
            raise HTTPException(status_code=500, detail="Registration failed")

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: UserResponse = Depends(get_current_user)
):
    """Logout user and blacklist their token"""
    try:
        token = credentials.credentials
        success = await logout_user(token)
        
        if success:
            logger.info(f"User {current_user.uid} logged out successfully")
            return LogoutResponse(
                success=True,
                message="Logged out successfully",
                timestamp=current_user.created_at
            )
        else:
            raise HTTPException(status_code=500, detail="Logout failed")
            
    except Exception as e:
        logger.error(f"Logout error for user {current_user.uid}: {e}")
        raise HTTPException(status_code=500, detail="Logout failed")

@router.post("/logout-all-sessions")
async def logout_all_sessions(
    current_user: UserResponse = Depends(get_current_user)
):
    """Logout user from all devices by revoking all refresh tokens"""
    try:
        revoke_user_tokens(current_user.uid)
        logger.info(f"All sessions revoked for user {current_user.uid}")
        
        return {
            "success": True,
            "message": "All sessions logged out successfully",
            "timestamp": current_user.created_at
        }
        
    except Exception as e:
        logger.error(f"Failed to revoke all sessions for user {current_user.uid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to logout all sessions")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get current user information"""
    return current_user

@router.get("/user-info/{uid}")
async def get_user_info(
    uid: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get user information (admin only or self)"""
    try:
        # Users can only get their own info unless they're admins
        if current_user.uid != uid:
            # Check if current user is admin in any group where target user is a member
            from procur.core.dependencies import validate_user_permissions
            has_permission = await validate_user_permissions(uid, current_user, require_self_or_admin=True)
            
            if not has_permission:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        # Get user info from Firebase Auth
        user_info = get_user_info(uid)
        
        if not user_info:
            raise HTTPException(status_code=404, detail="User not found")
        
        return user_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user info for {uid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get user information")

@router.post("/refresh-token")
async def refresh_token(
    current_user: UserResponse = Depends(get_current_user)
):
    """Refresh user's authentication token"""
    try:
        # In Firebase, tokens are automatically refreshed by the client
        # This endpoint can be used to validate the current token and return user info
        logger.info(f"Token refresh requested for user {current_user.uid}")
        
        return {
            "success": True,
            "message": "Token is valid",
            "user": current_user,
            "timestamp": current_user.created_at
        }
        
    except Exception as e:
        logger.error(f"Token refresh error for user {current_user.uid}: {e}")
        raise HTTPException(status_code=500, detail="Token refresh failed")

@router.get("/health")
async def auth_health_check():
    """Health check endpoint for authentication service"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": "2024-01-01T00:00:00Z"
    }