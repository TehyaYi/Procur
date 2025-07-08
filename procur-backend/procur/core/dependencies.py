from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from procur.core.firebase import verify_firebase_token, get_firestore_client
from procur.models.schemas import UserResponse, UserRole
from typing import Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        decoded_token = verify_firebase_token(token)
        uid = decoded_token['uid']
        
        # Get user from Firestore
        db = get_firestore_client()
        user_doc = db.collection('users').document(uid).get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_doc.to_dict()
        return UserResponse(uid=uid, **user_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(status_code=401, detail="Invalid authentication token")

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserResponse]:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None

async def require_group_admin(
    group_id: str,
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """Require user to be admin of specified group"""
    try:
        db = get_firestore_client()
        
        # Check if user is admin of the group
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if not member_doc.exists:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        member_data = member_doc.to_dict()
        if member_data.get('role') != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Group admin check error: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify group admin status")

async def require_group_member(
    group_id: str,
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """Require user to be member of specified group"""
    try:
        db = get_firestore_client()
        
        # Check if user is member of the group
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if not member_doc.exists:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        return current_user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Group member check error: {e}")
        raise HTTPException(status_code=500, detail="Failed to verify group membership")
    