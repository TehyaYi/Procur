from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from procur.core.firebase import verify_firebase_token, get_firestore_client, blacklist_token
from procur.models.schemas import UserResponse, UserRole
from typing import Optional
import logging
from datetime import datetime
import time

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Security configuration
MAX_AUTH_ATTEMPTS = 5
AUTH_RATE_LIMIT_WINDOW = 60  # seconds
TOKEN_MAX_AGE = 24 * 60 * 60  # 24 hours

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None
) -> UserResponse:
    """Get current authenticated user with enhanced security"""
    start_time = time.time()
    
    try:
        token = credentials.credentials
        
        # Log authentication attempt
        client_ip = request.client.host if request else "unknown"
        user_agent = request.headers.get("user-agent", "unknown") if request else "unknown"
        
        logger.info(f"Authentication attempt from IP: {client_ip}, User-Agent: {user_agent}")
        
        # Verify Firebase token with enhanced security
        decoded_token = verify_firebase_token(token, check_rate_limit=True)
        uid = decoded_token['uid']
        
        # Additional security checks
        current_time = datetime.utcnow().timestamp()
        
        # Check token age
        if 'iat' in decoded_token:
            token_age = current_time - decoded_token['iat']
            if token_age > TOKEN_MAX_AGE:
                logger.warning(f"Token too old for user {uid}, age: {token_age} seconds")
                raise HTTPException(status_code=401, detail="Token is too old. Please re-authenticate.")
        
        # Check if user account is disabled
        if decoded_token.get('disabled', False):
            logger.warning(f"Disabled user {uid} attempted authentication")
            raise HTTPException(status_code=401, detail="User account is disabled")
        
        # Get user from Firestore
        db = get_firestore_client()
        user_doc = db.collection('users').document(uid).get()
        
        if not user_doc.exists:
            logger.warning(f"User {uid} not found in database")
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_doc.to_dict()
        
        # Check if user is active in the system
        if user_data.get('status') == 'inactive':
            logger.warning(f"Inactive user {uid} attempted authentication")
            raise HTTPException(status_code=401, detail="User account is inactive")
        
        # Log successful authentication
        auth_time = time.time() - start_time
        logger.info(f"Successful authentication for user {uid} in {auth_time:.3f}s from IP: {client_ip}")
        
        return UserResponse(uid=uid, **user_data)
        
    except HTTPException:
        raise
    except ValueError as e:
        # Handle specific validation errors
        logger.warning(f"Token validation failed: {e}")
        if "expired" in str(e).lower():
            raise HTTPException(status_code=401, detail="Token has expired")
        elif "too old" in str(e).lower():
            raise HTTPException(status_code=401, detail="Token is too old. Please re-authenticate.")
        elif "revoked" in str(e).lower():
            raise HTTPException(status_code=401, detail="Token has been revoked")
        elif "rate limit" in str(e).lower():
            raise HTTPException(status_code=429, detail="Too many authentication attempts. Please try again later.")
        else:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    request: Request = None
) -> Optional[UserResponse]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, request)
    except HTTPException:
        return None

async def logout_user(token: str) -> bool:
    """Logout user by blacklisting their token"""
    try:
        blacklist_token(token)
        logger.info("User logged out successfully")
        return True
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        return False

async def require_group_admin(
    current_user: UserResponse = Depends(get_current_user),
    request: Request = None
) -> UserResponse:
    """Require user to be admin of specified group with audit logging"""
    start_time = time.time()
    client_ip = request.client.host if request else "unknown"
    
    try:
        # Extract group_id from the request path parameters or body
        group_id = None
        if request and request.path_params:
            group_id = request.path_params.get("group_id")
        
        # If not in path params, try to get from request body (for POST requests)
        if not group_id and request and request.method == "POST":
            try:
                body = await request.body()
                if body:
                    import json
                    body_data = json.loads(body)
                    group_id = body_data.get("group_id")
            except:
                pass
        
        if not group_id:
            raise HTTPException(status_code=400, detail="Group ID not found in request")
        
        logger.info(f"Admin access check for user {current_user.uid} to group {group_id} from IP: {client_ip}")
        
        db = get_firestore_client()
        
        # Check if user is admin of the group
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if not member_doc.exists:
            logger.warning(f"User {current_user.uid} attempted admin access to non-member group {group_id}")
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        member_data = member_doc.to_dict()
        if member_data.get('role') != UserRole.ADMIN:
            logger.warning(f"User {current_user.uid} attempted admin access without privileges to group {group_id}")
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Log successful admin access
        access_time = time.time() - start_time
        logger.info(f"Admin access granted for user {current_user.uid} to group {group_id} in {access_time:.3f}s")
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Group admin check error for user {current_user.uid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify group admin status")

async def require_group_member(
    current_user: UserResponse = Depends(get_current_user),
    request: Request = None
) -> UserResponse:
    """Require user to be member of specified group with audit logging"""
    start_time = time.time()
    client_ip = request.client.host if request else "unknown"
    
    try:
        # Extract group_id from the request path parameters or body
        group_id = None
        if request and request.path_params:
            group_id = request.path_params.get("group_id")
        
        # If not in path params, try to get from request body (for POST requests)
        if not group_id and request and request.method == "POST":
            try:
                body = await request.body()
                if body:
                    import json
                    body_data = json.loads(body)
                    group_id = body_data.get("group_id")
            except:
                pass
        
        if not group_id:
            raise HTTPException(status_code=400, detail="Group ID not found in request")
        
        logger.info(f"Member access check for user {current_user.uid} to group {group_id} from IP: {client_ip}")
        
        db = get_firestore_client()
        
        # Check if user is member of the group
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if not member_doc.exists:
            logger.warning(f"User {current_user.uid} attempted member access to non-member group {group_id}")
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        # Log successful member access
        access_time = time.time() - start_time
        logger.info(f"Member access granted for user {current_user.uid} to group {group_id} in {access_time:.3f}s")
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Group member check error for user {current_user.uid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify group membership")

async def enforce_group_privacy(
    group_id: str,
    current_user: Optional[UserResponse] = None,
    request: Request = None
) -> bool:
    """Enforce group privacy settings and return access status with audit logging"""
    start_time = time.time()
    client_ip = request.client.host if request else "unknown"
    
    try:
        logger.info(f"Privacy check for group {group_id} from IP: {client_ip}, user: {current_user.uid if current_user else 'anonymous'}")
        
        db = get_firestore_client()
        group_doc = db.collection('groups').document(group_id).get()
        
        if not group_doc.exists:
            logger.warning(f"Privacy check failed: group {group_id} not found")
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group_doc.to_dict()
        
        # Public groups: anyone can access
        if group_data['privacy'] == 'public':
            logger.info(f"Public group {group_id} access granted to {current_user.uid if current_user else 'anonymous'}")
            return True
        
        # Private/Invite-only: require authentication
        if not current_user:
            logger.warning(f"Unauthenticated access attempt to private group {group_id} from IP: {client_ip}")
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Check membership
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists:
            logger.warning(f"User {current_user.uid} attempted access to private group {group_id} without membership")
            raise HTTPException(status_code=403, detail="Access denied - not a member of this group")
        
        # Log successful access
        access_time = time.time() - start_time
        logger.info(f"Private group {group_id} access granted to user {current_user.uid} in {access_time:.3f}s")
        
        return True
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Group privacy enforcement error for group {group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify group access")

async def get_user_group_role(
    group_id: str,
    current_user: UserResponse
) -> Optional[UserRole]:
    """Get user's role in a specific group"""
    try:
        db = get_firestore_client()
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if member_doc.exists:
            role = member_doc.to_dict().get('role')
            logger.debug(f"User {current_user.uid} has role {role} in group {group_id}")
            return role
        return None
        
    except Exception as e:
        logger.error(f"Failed to get user group role for user {current_user.uid} in group {group_id}: {e}")
        return None

async def validate_user_permissions(
    user_id: str,
    current_user: UserResponse,
    require_self_or_admin: bool = True
) -> bool:
    """Validate if current user can perform actions on target user"""
    try:
        # Users can always perform actions on themselves
        if current_user.uid == user_id:
            return True
        
        # If admin check is required, verify admin status
        if require_self_or_admin:
            # Check if current user is a system admin (you can implement this based on your needs)
            if current_user.role == UserRole.SYSTEM_ADMIN:
                return True
            
            # Check if current user is admin in any group where target user is a member
            db = get_firestore_client()
            groups = db.collection('groups').stream()
            
            for group in groups:
                member_doc = group.reference.collection('members').document(current_user.uid).get()
                if member_doc.exists and member_doc.to_dict().get('role') == UserRole.ADMIN:
                    # Check if target user is also in this group
                    target_member_doc = group.reference.collection('members').document(user_id).get()
                    if target_member_doc.exists:
                        logger.info(f"Admin access granted for user {current_user.uid} to manage user {user_id} in group {group.id}")
                        return True
        
        return False
        
    except Exception as e:
        logger.error(f"Permission validation error: {e}")
        return False
    