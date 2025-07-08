from fastapi import APIRouter, HTTPException, Depends
from procur.core.dependencies import get_current_user, get_optional_user
from procur.models.schemas import UserResponse, ReactAPIResponse, DashboardData
from procur.core.firebase import verify_firebase_token, get_firestore_client
from typing import Optional
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/verify-token", response_model=ReactAPIResponse)
async def verify_token(current_user: UserResponse = Depends(get_current_user)):
    """Verify Firebase ID token and return user info for React app"""
    try:
        # Get additional user stats for React dashboard
        db = get_firestore_client()
        
        # Count user's groups
        user_groups = []
        all_groups = db.collection('groups').where('is_active', '==', True).get()
        
        for group_doc in all_groups:
            group_id = group_doc.id
            member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
            if member_doc.exists:
                user_groups.append(group_doc.to_dict())
        
        # Count pending join requests (if user is admin)
        pending_requests = 0
        for group in user_groups:
            if group.get('admin_id') == current_user.uid:
                requests = db.collection('join_requests').where('group_id', '==', group['id']).where('status', '==', 'pending').get()
                pending_requests += len(requests)
        
        return ReactAPIResponse(
            success=True,
            message="Token verified successfully",
            data={
                "user": current_user.dict(),
                "stats": {
                    "groups_count": len(user_groups),
                    "pending_requests": pending_requests,
                    "admin_groups": len([g for g in user_groups if g.get('admin_id') == current_user.uid])
                }
            },
            meta={
                "authenticated": True,
                "token_valid": True
            }
        )
        
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")

@router.get("/me", response_model=ReactAPIResponse)
async def get_current_user_info(current_user: UserResponse = Depends(get_current_user)):
    """Get current user information with React-specific data"""
    return ReactAPIResponse(
        success=True,
        message="User info retrieved",
        data={"user": current_user.dict()}
    )

@router.post("/refresh", response_model=ReactAPIResponse)
async def refresh_user_data(current_user: UserResponse = Depends(get_current_user)):
    """Refresh user data from database (for React state updates)"""
    try:
        db = get_firestore_client()
        
        # Get fresh user data from Firestore
        user_doc = db.collection('users').document(current_user.uid).get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        fresh_user_data = user_doc.to_dict()
        fresh_user = UserResponse(uid=current_user.uid, **fresh_user_data)
        
        return ReactAPIResponse(
            success=True,
            message="User data refreshed",
            data={"user": fresh_user.dict()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User refresh error: {e}")
        raise HTTPException(status_code=500, detail="Failed to refresh user data")

@router.get("/dashboard", response_model=ReactAPIResponse)
async def get_dashboard_data(current_user: UserResponse = Depends(get_current_user)):
    """Get comprehensive dashboard data for React app"""
    try:
        db = get_firestore_client()
        
        # Get user's groups with role information
        user_groups = []
        all_groups = db.collection('groups').where('is_active', '==', True).get()
        
        for group_doc in all_groups:
            group_id = group_doc.id
            member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
            if member_doc.exists:
                group_data = group_doc.to_dict()
                member_data = member_doc.to_dict()
                group_data['user_role'] = member_data.get('role')
                group_data['joined_at'] = member_data.get('joined_at')
                user_groups.append(group_data)
        
        # Get recent notifications (placeholder - implement notification system)
        recent_notifications = []
        
        # Get pending requests for admin groups
        pending_requests = []
        admin_groups = [g for g in user_groups if g.get('admin_id') == current_user.uid]
        
        for group in admin_groups:
            requests = db.collection('join_requests').where('group_id', '==', group['id']).where('status', '==', 'pending').order_by('created_at', direction='DESCENDING').limit(5).get()
            for req_doc in requests:
                req_data = req_doc.to_dict()
                req_data['group_name'] = group['name']
                pending_requests.append(req_data)
        
        # Calculate statistics
        stats = {
            "total_groups": len(user_groups),
            "admin_groups": len(admin_groups),
            "member_groups": len([g for g in user_groups if g.get('admin_id') != current_user.uid]),
            "pending_requests": len(pending_requests),
            "total_members": sum(g.get('member_count', 0) for g in admin_groups)
        }
        
        dashboard_data = {
            "user": current_user.dict(),
            "groups": user_groups,
            "recent_notifications": recent_notifications,
            "pending_requests": pending_requests[:5],  # Last 5 requests
            "stats": stats
        }
        
        return ReactAPIResponse(
            success=True,
            message="Dashboard data retrieved",
            data=dashboard_data,
            meta={
                "last_updated": "2025-01-01T00:00:00Z",
                "groups_count": len(user_groups)
            }
        )
        
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        raise HTTPException(status_code=500, detail="Failed to load dashboard data")

@router.post("/logout", response_model=ReactAPIResponse)
async def logout():
    """Logout endpoint for React app (client-side token cleanup)"""
    return ReactAPIResponse(
        success=True,
        message="Logged out successfully",
        meta={"redirect": "/login"}
    )

@router.get("/check", response_model=ReactAPIResponse)
async def check_authentication(current_user: Optional[UserResponse] = Depends(get_optional_user)):
    """Check authentication status for React app (non-protected route)"""
    if current_user:
        return ReactAPIResponse(
            success=True,
            message="User is authenticated",
            data={"user": current_user.dict()},
            meta={"authenticated": True}
        )
    else:
        return ReactAPIResponse(
            success=True,
            message="User is not authenticated",
            data={"user": None},
            meta={"authenticated": False}
        )

# EOF