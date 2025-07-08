from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from procur.core.dependencies import get_current_user
from procur.models.schemas import (
    UserCreate, UserUpdate, UserResponse, GroupResponse,
    ReactAPIResponse, ReactErrorResponse
)
from procur.core.firebase import get_firestore_client
from procur.services.email_service import email_service
from procur.templates.email_templates import EmailTemplate
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=ReactAPIResponse)
async def register_user(
    user_data: UserCreate,
    background_tasks: BackgroundTasks
):
    """Register a new user (React-friendly response)"""
    try:
        db = get_firestore_client()
        
        # Check if user already exists
        user_doc = db.collection('users').document(user_data.uid).get()
        if user_doc.exists:
            return ReactAPIResponse(
                success=False,
                message="User already registered",
                data={"existing_user": True}
            )
        
        # Create user document
        user_dict = user_data.dict()
        user_dict.update({
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'is_active': True,
            'avatar_url': None,
            'bio': None
        })
        
        db.collection('users').document(user_data.uid).set(user_dict)
        
        # Send welcome email
        background_tasks.add_task(send_welcome_email, user_data.email, user_data.display_name)
        
        new_user = UserResponse(**user_dict)
        
        return ReactAPIResponse(
            success=True,
            message="User registered successfully",
            data={
                "user": new_user.dict(),
                "first_time": True
            },
            meta={
                "next_steps": [
                    "Complete your profile",
                    "Browse available groups",
                    "Join your first buying group"
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to register user: {e}")
        return ReactErrorResponse(
            error="Registration failed",
            error_code="REGISTRATION_ERROR",
            details={"message": str(e)}
        )

@router.get("/profile", response_model=ReactAPIResponse)
async def get_user_profile(current_user: UserResponse = Depends(get_current_user)):
    """Get current user profile with React-specific enhancements"""
    try:
        db = get_firestore_client()
        
        # Get fresh user data
        user_doc = db.collection('users').document(current_user.uid).get()
        user_data = user_doc.to_dict()
        
        # Calculate profile completion percentage
        profile_fields = ['display_name', 'company_name', 'industry', 'phone', 'bio', 'avatar_url']
        completed_fields = sum(1 for field in profile_fields if user_data.get(field))
        profile_completion = (completed_fields / len(profile_fields)) * 100
        
        # Get user's group memberships
        groups_count = 0
        admin_count = 0
        all_groups = db.collection('groups').where('is_active', '==', True).get()
        
        for group_doc in all_groups:
            member_doc = db.collection('groups').document(group_doc.id).collection('members').document(current_user.uid).get()
            if member_doc.exists:
                groups_count += 1
                if member_doc.to_dict().get('role') == 'admin':
                    admin_count += 1
        
        return ReactAPIResponse(
            success=True,
            message="Profile retrieved successfully",
            data={
                "user": user_data,
                "profile_completion": profile_completion,
                "stats": {
                    "groups_joined": groups_count,
                    "groups_admin": admin_count,
                    "member_since": user_data.get('created_at')
                }
            },
            meta={
                "profile_complete": profile_completion >= 80,
                "missing_fields": [field for field in profile_fields if not user_data.get(field)]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve profile")

@router.put("/profile", response_model=ReactAPIResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Update user profile with validation feedback for React forms"""
    try:
        db = get_firestore_client()
        
        # Prepare update data
        update_data = {k: v for k, v in user_update.dict().items() if v is not None}
        if update_data:
            update_data['updated_at'] = datetime.utcnow()
            
            # Update user document
            db.collection('users').document(current_user.uid).update(update_data)
            
            # Get updated user data
            updated_doc = db.collection('users').document(current_user.uid).get()
            updated_user_data = updated_doc.to_dict()
            
            # Recalculate profile completion
            profile_fields = ['display_name', 'company_name', 'industry', 'phone', 'bio', 'avatar_url']
            completed_fields = sum(1 for field in profile_fields if updated_user_data.get(field))
            profile_completion = (completed_fields / len(profile_fields)) * 100
            
            return ReactAPIResponse(
                success=True,
                message="Profile updated successfully",
                data={
                    "user": updated_user_data,
                    "profile_completion": profile_completion,
                    "updated_fields": list(update_data.keys())
                },
                meta={
                    "profile_complete": profile_completion >= 80,
                    "last_updated": update_data['updated_at'].isoformat()
                }
            )
        else:
            return ReactAPIResponse(
                success=False,
                message="No fields to update",
                data={"user": current_user.dict()}
            )
        
    except Exception as e:
        logger.error(f"Failed to update user profile: {e}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

@router.get("/groups", response_model=ReactAPIResponse)
async def get_user_groups(current_user: UserResponse = Depends(get_current_user)):
    """Get groups that user is a member of (React component data)"""
    try:
        db = get_firestore_client()
        
        # Find all groups where user is a member
        user_groups = []
        admin_groups = []
        member_groups = []
        
        # Query all active groups
        all_groups = db.collection('groups').where('is_active', '==', True).get()
        
        for group_doc in all_groups:
            group_id = group_doc.id
            group_data = group_doc.to_dict()
            
            # Check if user is member of this group
            member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
            
            if member_doc.exists:
                member_data = member_doc.to_dict()
                role = member_data.get('role')
                
                # Add role and membership info to group data
                group_data['user_role'] = role
                group_data['joined_at'] = member_data.get('joined_at')
                
                user_groups.append(group_data)
                
                if role == 'admin':
                    admin_groups.append(group_data)
                else:
                    member_groups.append(group_data)
        
        return ReactAPIResponse(
            success=True,
            message="User groups retrieved",
            data={
                "all_groups": user_groups,
                "admin_groups": admin_groups,
                "member_groups": member_groups,
                "stats": {
                    "total": len(user_groups),
                    "admin": len(admin_groups),
                    "member": len(member_groups)
                }
            },
            meta={
                "has_groups": len(user_groups) > 0,
                "is_group_admin": len(admin_groups) > 0
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get user groups: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user groups")

@router.get("/notifications", response_model=ReactAPIResponse)
async def get_user_notifications(
    limit: int = 20,
    unread_only: bool = False,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get user notifications for React notification center"""
    try:
        # Placeholder for notification system - implement based on your needs
        notifications = []
        
        # For now, return pending join requests as notifications for group admins
        db = get_firestore_client()
        
        # Get admin groups
        admin_groups = []
        all_groups = db.collection('groups').where('is_active', '==', True).get()
        
        for group_doc in all_groups:
            group_data = group_doc.to_dict()
            if group_data.get('admin_id') == current_user.uid:
                admin_groups.append(group_data)
        
        # Get pending join requests as notifications
        for group in admin_groups:
            requests = db.collection('join_requests').where('group_id', '==', group['id']).where('status', '==', 'pending').order_by('created_at', direction='DESCENDING').limit(5).get()
            
            for req_doc in requests:
                req_data = req_doc.to_dict()
                notifications.append({
                    "id": req_doc.id,
                    "type": "join_request",
                    "title": f"New join request for {group['name']}",
                    "message": f"{req_data['user_name']} wants to join your group",
                    "data": {
                        "group_id": group['id'],
                        "group_name": group['name'],
                        "requester_name": req_data['user_name'],
                        "request_id": req_doc.id
                    },
                    "read": False,
                    "created_at": req_data['created_at']
                })
        
        # Sort by creation date
        notifications.sort(key=lambda x: x['created_at'], reverse=True)
        
        # Apply filters
        if unread_only:
            notifications = [n for n in notifications if not n['read']]
        
        notifications = notifications[:limit]
        
        return ReactAPIResponse(
            success=True,
            message="Notifications retrieved",
            data={
                "notifications": notifications,
                "unread_count": len([n for n in notifications if not n['read']])
            },
            meta={
                "total": len(notifications),
                "has_unread": any(not n['read'] for n in notifications)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve notifications")

@router.delete("/profile", response_model=ReactAPIResponse)
async def delete_user_account(current_user: UserResponse = Depends(get_current_user)):
    """Delete user account with React confirmation flow"""
    try:
        db = get_firestore_client()
        
        # Check if user is admin of any groups
        admin_groups = []
        all_groups = db.collection('groups').where('is_active', '==', True).get()
        
        for group_doc in all_groups:
            group_data = group_doc.to_dict()
            if group_data.get('admin_id') == current_user.uid:
                admin_groups.append(group_data)
        
        if admin_groups:
            return ReactAPIResponse(
                success=False,
                message="Cannot delete account while managing groups",
                data={
                    "admin_groups": admin_groups,
                    "action_required": "transfer_admin_rights"
                },
                meta={
                    "deletion_blocked": True,
                    "reason": "admin_of_groups"
                }
            )
        
        # Soft delete - mark as inactive
        db.collection('users').document(current_user.uid).update({
            'is_active': False,
            'deleted_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        # Remove from all groups
        for group_doc in all_groups:
            member_doc = db.collection('groups').document(group_doc.id).collection('members').document(current_user.uid).get()
            if member_doc.exists:
                # Remove member
                db.collection('groups').document(group_doc.id).collection('members').document(current_user.uid).delete()
                # Update member count
                db.collection('groups').document(group_doc.id).update({
                    'member_count': max(0, group_doc.to_dict().get('member_count', 1) - 1)
                })
        
        return ReactAPIResponse(
            success=True,
            message="Account deleted successfully",
            meta={
                "deletion_complete": True,
                "redirect": "/goodbye"
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to delete user account: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")

# Background task helper functions
async def send_welcome_email(email: str, name: str):
    """Send welcome email to new users"""
    try:
        template = EmailTemplate(
            subject="Welcome to Procur! 🎉",
            html_body=f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h1 style="color: #007bff;">Welcome to Procur, {name}! 🎉</h1>
                    <p>Thank you for joining our platform. You're now part of a community that's revolutionizing group purchasing for businesses.</p>
                    
                    <h2>What's Next?</h2>
                    <ul>
                        <li>Complete your profile</li>
                        <li>Browse available buying groups</li>
                        <li>Join groups in your industry</li>
                        <li>Start saving with group purchasing power</li>
                    </ul>
                    
                    <p>If you have any questions, don't hesitate to reach out to our support team.</p>
                    
                    <p>Happy buying!<br>The Procur Team</p>
                </div>
            </body>
            </html>
            """,
            text_body=f"""
            Welcome to Procur, {name}!
            
            Thank you for joining our platform. You're now part of a community that's revolutionizing group purchasing for businesses.
            
            What's Next?
            - Complete your profile
            - Browse available buying groups  
            - Join groups in your industry
            - Start saving with group purchasing power
            
            If you have any questions, don't hesitate to reach out to our support team.
            
            Happy buying!
            The Procur Team
            """
        )
        
        await email_service.send_email(email, template)
        
    except Exception as e:
        logger.error(f"Failed to send welcome email: {e}")

# EOF