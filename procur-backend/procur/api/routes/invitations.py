from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from procur.core.dependencies import (
    get_current_user, get_optional_user, require_group_admin
)
from procur.models.schemas import (
    InvitationCreate, InvitationResponse, InvitationValidateResponse,
    UserResponse, ReactAPIResponse
)
from procur.core.firebase import get_firestore_client
from procur.services.email_service import email_service
from procur.templates.email_templates import EmailTemplate
from procur.core.config import get_settings
from google.cloud.firestore import Increment
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import secrets
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=ReactAPIResponse)
async def create_invitation(
    invitation_data: InvitationCreate,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(require_group_admin)
):
    """Create group invitation link with React-friendly response"""
    try:
        db = get_firestore_client()
        
        # Get group details
        group_doc = db.collection('groups').document(invitation_data.group_id).get()
        if not group_doc.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group_doc.to_dict()
        
        # Create invitation
        invitation_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        
        settings = get_settings()
        
        invitation = {
            'id': invitation_id,
            'group_id': invitation_data.group_id,
            'group_name': group_data['name'],
            'token': token,
            'created_by': current_user.uid,
            'expires_at': datetime.utcnow() + timedelta(days=invitation_data.expires_in_days),
            'max_uses': invitation_data.max_uses,
            'current_uses': 0,
            'is_active': True,
            'created_at': datetime.utcnow()
        }
        
        db.collection('invitations').document(invitation_id).set(invitation)
        
        # Generate invitation URL
        invitation_url = f"{settings.FRONTEND_URL}/join/{token}"
        
        # Send emails if email list provided
        emails_sent = 0
        if invitation_data.email_list:
            background_tasks.add_task(
                send_invitation_emails,
                invitation_data.email_list,
                group_data['name'],
                token,
                current_user.display_name,
                invitation_url
            )
            emails_sent = len(invitation_data.email_list)
        
        invitation_response = InvitationResponse(**invitation)
        
        return ReactAPIResponse(
            success=True,
            message="Invitation created successfully",
            data={
                "invitation": invitation_response.dict(),
                "invitation_url": invitation_url,
                "emails_sent": emails_sent
            },
            meta={
                "shareable_link": invitation_url,
                "expires_in_days": invitation_data.expires_in_days,
                "bulk_emails_sent": emails_sent > 0
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to create invitation")

@router.get("/validate/{token}", response_model=ReactAPIResponse)
async def validate_invitation(token: str):
    """Validate invitation token (public endpoint)"""
    try:
        db = get_firestore_client()
        
        # Find invitation by token
        invitations = db.collection('invitations').where('token', '==', token).where('is_active', '==', True).get()
        
        if not invitations:
            return ReactAPIResponse(
                success=False,
                message="Invalid or expired invitation",
                data={"is_valid": False}
            )
        
        invitation_doc = invitations[0]
        invitation_data = invitation_doc.to_dict()
        
        # Check if expired
        if invitation_data['expires_at'] < datetime.utcnow():
            return ReactAPIResponse(
                success=False,
                message="Invitation has expired",
                data={"is_valid": False, "reason": "expired"}
            )
        
        # Check usage limits
        if invitation_data.get('max_uses') and invitation_data['current_uses'] >= invitation_data['max_uses']:
            return ReactAPIResponse(
                success=False,
                message="Invitation usage limit reached",
                data={"is_valid": False, "reason": "usage_limit"}
            )
        
        # Get group details
        group_doc = db.collection('groups').document(invitation_data['group_id']).get()
        if not group_doc.exists:
            return ReactAPIResponse(
                success=False,
                message="Group not found",
                data={"is_valid": False, "reason": "group_not_found"}
            )
        
        group_data = group_doc.to_dict()
        
        return ReactAPIResponse(
            success=True,
            message="Valid invitation",
            data={
                "is_valid": True,
                "group_id": invitation_data['group_id'],
                "group_name": group_data['name'],
                "group_description": group_data['description'],
                "group_industry": group_data['industry'],
                "expires_at": invitation_data['expires_at'],
                "uses_remaining": invitation_data.get('max_uses') - invitation_data['current_uses'] if invitation_data.get('max_uses') else None,
                "invitation_id": invitation_doc.id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to validate invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to validate invitation")

@router.post("/join/{token}", response_model=ReactAPIResponse)
async def join_via_invitation(
    token: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Join group via invitation token"""
    try:
        db = get_firestore_client()
        
        # Find invitation by token
        invitations = db.collection('invitations').where('token', '==', token).where('is_active', '==', True).get()
        
        if not invitations:
            raise HTTPException(status_code=400, detail="Invalid or expired invitation")
        
        invitation_doc = invitations[0]
        invitation_data = invitation_doc.to_dict()
        
        # Check if expired
        if invitation_data['expires_at'] < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Invitation has expired")
        
        # Check usage limits
        if invitation_data.get('max_uses') and invitation_data['current_uses'] >= invitation_data['max_uses']:
            raise HTTPException(status_code=400, detail="Invitation usage limit reached")
        
        group_id = invitation_data['group_id']
        
        # Check if user is already a member
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if member_doc.exists:
            raise HTTPException(status_code=400, detail="Already a member of this group")
        
        # Check if there's a pending join request
        existing_requests = db.collection('join_requests').where('group_id', '==', group_id).where('user_id', '==', current_user.uid).where('status', '==', 'pending').get()
        if len(existing_requests) > 0:
            raise HTTPException(status_code=400, detail="Join request already pending")
        
        # Add user to group
        member_data = {
            'user_id': current_user.uid,
            'role': 'member',
            'joined_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        db.collection('groups').document(group_id).collection('members').document(current_user.uid).set(member_data)
        
        # Increment member count
        db.collection('groups').document(group_id).update({
            'member_count': Increment(1)
        })
        
        # Increment invitation usage
        db.collection('invitations').document(invitation_doc.id).update({
            'current_uses': Increment(1)
        })
        
        # Get group details for response
        group_doc = db.collection('groups').document(group_id).get()
        group_data = group_doc.to_dict()
        
        return ReactAPIResponse(
            success=True,
            message=f"Successfully joined '{group_data['name']}'",
            data={
                "group_id": group_id,
                "group_name": group_data['name'],
                "user_role": "member"
            },
            meta={
                "redirect": f"/groups/{group_id}",
                "next_steps": [
                    "Explore group products",
                    "Connect with other members",
                    "Start purchasing"
                ]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to join via invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to join group")

@router.get("/group/{group_id}", response_model=ReactAPIResponse)
async def get_group_invitations(
    group_id: str,
    current_user: UserResponse = Depends(require_group_admin)
):
    """Get all invitations for a group (admin only)"""
    try:
        db = get_firestore_client()
        
        # Get invitations for the group
        invitations_docs = db.collection('invitations').where('group_id', '==', group_id).order_by('created_at', direction='DESCENDING').get()
        
        invitations = []
        for inv_doc in invitations_docs:
            inv_data = inv_doc.to_dict()
            
            # Calculate status
            is_expired = inv_data['expires_at'] < datetime.utcnow()
            is_used_up = inv_data.get('max_uses') and inv_data['current_uses'] >= inv_data['max_uses']
            
            inv_data['status'] = 'active'
            if is_expired:
                inv_data['status'] = 'expired'
            elif is_used_up:
                inv_data['status'] = 'used_up'
            
            invitations.append(inv_data)
        
        # Calculate stats
        active_count = len([i for i in invitations if i['status'] == 'active'])
        expired_count = len([i for i in invitations if i['status'] == 'expired'])
        used_up_count = len([i for i in invitations if i['status'] == 'used_up'])
        
        return ReactAPIResponse(
            success=True,
            message="Group invitations retrieved",
            data={
                "invitations": invitations,
                "stats": {
                    "total": len(invitations),
                    "active": active_count,
                    "expired": expired_count,
                    "used_up": used_up_count
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get group invitations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve invitations")

@router.delete("/{invitation_id}", response_model=ReactAPIResponse)
async def deactivate_invitation(
    invitation_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Deactivate invitation (admin only)"""
    try:
        db = get_firestore_client()
        
        # Get invitation
        invitation_doc = db.collection('invitations').document(invitation_id).get()
        if not invitation_doc.exists:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        invitation_data = invitation_doc.to_dict()
        group_id = invitation_data['group_id']
        
        # Verify admin privileges by checking group membership directly
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if not member_doc.exists:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        member_data = member_doc.to_dict()
        if member_data.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Deactivate invitation
        db.collection('invitations').document(invitation_id).update({
            'is_active': False,
            'deactivated_at': datetime.utcnow(),
            'deactivated_by': current_user.uid
        })
        
        return ReactAPIResponse(
            success=True,
            message="Invitation deactivated",
            data={"invitation_id": invitation_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deactivate invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to deactivate invitation")

@router.post("/{invitation_id}/regenerate", response_model=ReactAPIResponse)
async def regenerate_invitation_token(
    invitation_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Regenerate invitation token (admin only)"""
    try:
        db = get_firestore_client()
        
        # Get invitation
        invitation_doc = db.collection('invitations').document(invitation_id).get()
        if not invitation_doc.exists:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        invitation_data = invitation_doc.to_dict()
        group_id = invitation_data['group_id']
        
        # Verify admin privileges by checking group membership directly
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if not member_doc.exists:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        member_data = member_doc.to_dict()
        if member_data.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        
        # Update invitation
        db.collection('invitations').document(invitation_id).update({
            'token': new_token,
            'current_uses': 0,
            'is_active': True,
            'regenerated_at': datetime.utcnow(),
            'regenerated_by': current_user.uid
        })
        
        # Generate new invitation URL
        settings = get_settings()
        new_invitation_url = f"{settings.FRONTEND_URL}/join/{new_token}"
        
        return ReactAPIResponse(
            success=True,
            message="Invitation token regenerated",
            data={
                "invitation_id": invitation_id,
                "new_token": new_token,
                "new_invitation_url": new_invitation_url
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate invitation token: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate token")

@router.get("/my-invitations", response_model=ReactAPIResponse)
async def get_my_invitations(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get invitations created by current user"""
    try:
        db = get_firestore_client()
        
        # Get invitations created by user
        invitations_docs = db.collection('invitations').where('created_by', '==', current_user.uid).order_by('created_at', direction='DESCENDING').get()
        
        invitations = []
        for inv_doc in invitations_docs:
            inv_data = inv_doc.to_dict()
            
            # Get group details
            group_doc = db.collection('groups').document(inv_data['group_id']).get()
            if group_doc.exists:
                group_data = group_doc.to_dict()
                inv_data['group_name'] = group_data['name']
                inv_data['group_industry'] = group_data.get('industry')
            
            # Calculate status
            is_expired = inv_data['expires_at'] < datetime.utcnow()
            is_used_up = inv_data.get('max_uses') and inv_data['current_uses'] >= inv_data['max_uses']
            
            inv_data['status'] = 'active'
            if is_expired:
                inv_data['status'] = 'expired'
            elif is_used_up:
                inv_data['status'] = 'used_up'
            
            invitations.append(inv_data)
        
        return ReactAPIResponse(
            success=True,
            message="Your invitations retrieved",
            data={"invitations": invitations}
        )
        
    except Exception as e:
        logger.error(f"Failed to get user invitations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve invitations")

# Helper function for sending invitation emails
async def send_invitation_emails(
    email_list: List[str], 
    group_name: str, 
    token: str, 
    inviter_name: str,
    invitation_url: str
):
    """Send invitation emails to list of email addresses"""
    try:
        settings = get_settings()
        
        for email in email_list:
            try:
                # Create email template
                template = EmailTemplate(
                    subject=f"Join {group_name} - Group Purchasing Organization",
                    html_body=f"""
                    <h2>You're invited to join {group_name}!</h2>
                    <p>Hi there,</p>
                    <p>{inviter_name} has invited you to join their group purchasing organization.</p>
                    <p><strong>Group:</strong> {group_name}</p>
                    <p><strong>What you'll get:</strong></p>
                    <ul>
                        <li>Access to bulk purchasing discounts</li>
                        <li>Curated products for your industry</li>
                        <li>Network with other businesses</li>
                    </ul>
                    <p><a href="{invitation_url}" style="background-color: #007bff; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px;">Join Group Now</a></p>
                    <p>This invitation link will expire soon, so don't wait!</p>
                    <p>Best regards,<br>The Procur Team</p>
                    """,
                    text_body=f"""
                    You're invited to join {group_name}!
                    
                    Hi there,
                    
                    {inviter_name} has invited you to join their group purchasing organization.
                    
                    Group: {group_name}
                    
                    What you'll get:
                    - Access to bulk purchasing discounts
                    - Curated products for your industry
                    - Network with other businesses
                    
                    Join now: {invitation_url}
                    
                    This invitation link will expire soon, so don't wait!
                    
                    Best regards,
                    The Procur Team
                    """
                )
                
                # Send email
                await email_service.send_email(email, template)
                logger.info(f"Invitation email sent to {email}")
                
            except Exception as e:
                logger.error(f"Failed to send invitation email to {email}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Failed to send invitation emails: {e}")