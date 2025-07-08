from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from procur.core.dependencies import get_current_user, get_optional_user
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
    current_user: UserResponse = Depends(get_current_user)
):
    """Create group invitation link with React-friendly response"""
    try:
        db = get_firestore_client()
        
        # Verify user is admin of the group
        member_doc = db.collection('groups').document(invitation_data.group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists or member_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
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
    """Validate invitation token for React join page"""
    try:
        db = get_firestore_client()
        
        # Find invitation by token
        invitations = db.collection('invitations').where('token', '==', token).where('is_active', '==', True).get()
        
        if not invitations:
            return ReactAPIResponse(
                success=False,
                message="Invalid invitation token",
                data={
                    "is_valid": False,
                    "error_code": "INVALID_TOKEN"
                },
                meta={
                    "redirect": "/groups"
                }
            )
        
        invitation_doc = invitations[0]
        invitation_data = invitation_doc.to_dict()
        
        # Check if invitation is expired
        is_expired = datetime.utcnow() > invitation_data['expires_at']
        
        # Check usage limits
        max_uses = invitation_data.get('max_uses')
        current_uses = invitation_data.get('current_uses', 0)
        is_usage_exceeded = max_uses and current_uses >= max_uses
        
        is_valid = not is_expired and not is_usage_exceeded
        
        # Get group details
        group_doc = db.collection('groups').document(invitation_data['group_id']).get()
        if not group_doc.exists:
            return ReactAPIResponse(
                success=False,
                message="Group not found",
                data={
                    "is_valid": False,
                    "error_code": "GROUP_NOT_FOUND"
                }
            )
        
        group_data = group_doc.to_dict()
        
        # Calculate remaining uses
        uses_remaining = None
        if max_uses:
            uses_remaining = max(0, max_uses - current_uses)
        
        validation_data = {
            "is_valid": is_valid,
            "group_id": invitation_data['group_id'],
            "group_name": group_data['name'],
            "group_description": group_data['description'],
            "group_industry": group_data['industry'],
            "group_logo_url": group_data.get('logo_url'),
            "group_member_count": group_data.get('member_count', 0),
            "expires_at": invitation_data['expires_at'],
            "uses_remaining": uses_remaining,
            "invitation_expired": is_expired,
            "usage_exceeded": is_usage_exceeded
        }
        
        if is_valid:
            message = f"Valid invitation to join {group_data['name']}"
        elif is_expired:
            message = "This invitation has expired"
        elif is_usage_exceeded:
            message = "This invitation has reached its usage limit"
        else:
            message = "Invalid invitation"
        
        return ReactAPIResponse(
            success=is_valid,
            message=message,
            data=validation_data,
            meta={
                "can_join": is_valid,
                "requires_auth": True
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
    """Join group via invitation token with React state management"""
    try:
        db = get_firestore_client()
        
        # Validate invitation first
        validation_response = await validate_invitation(token)
        validation_data = validation_response.data
        
        if not validation_data.get('is_valid'):
            return ReactAPIResponse(
                success=False,
                message=validation_response.message,
                data={
                    "error_code": "INVALID_INVITATION",
                    "validation_error": validation_data
                }
            )
        
        group_id = validation_data['group_id']
        group_name = validation_data['group_name']
        
        # Check if user is already a member
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if member_doc.exists:
            return ReactAPIResponse(
                success=False,
                message="You are already a member of this group",
                data={
                    "error_code": "ALREADY_MEMBER",
                    "group": {
                        "id": group_id,
                        "name": group_name
                    }
                },
                meta={
                    "redirect": f"/groups/{group_id}"
                }
            )
        
        # Check group capacity
        group_doc = db.collection('groups').document(group_id).get()
        group_data = group_doc.to_dict()
        max_members = group_data.get('max_members')
        current_member_count = group_data.get('member_count', 0)
        
        if max_members and current_member_count >= max_members:
            return ReactAPIResponse(
                success=False,
                message="This group has reached its maximum capacity",
                data={
                    "error_code": "GROUP_FULL",
                    "max_members": max_members,
                    "current_members": current_member_count
                }
            )
        
        # Add user to group
        member_data = {
            'user_id': current_user.uid,
            'role': 'member',
            'joined_at': datetime.utcnow(),
            'joined_via': 'invitation',
            'invitation_token': token
        }
        
        db.collection('groups').document(group_id).collection('members').document(current_user.uid).set(member_data)
        
        # Update group member count
        group_ref = db.collection('groups').document(group_id)
        group_ref.update({'member_count': Increment(1)})
        
        # Update invitation usage
        invitations = db.collection('invitations').where('token', '==', token).get()
        if invitations:
            invitation_doc = invitations[0]
            invitation_ref = db.collection('invitations').document(invitation_doc.id)
            invitation_ref.update({'current_uses': Increment(1)})
        
        return ReactAPIResponse(
            success=True,
            message=f"Welcome to {group_name}!",
            data={
                "group": {
                    "id": group_id,
                    "name": group_name,
                    "description": validation_data['group_description'],
                    "industry": validation_data['group_industry'],
                    "logo_url": validation_data.get('group_logo_url'),
                    "member_count": current_member_count + 1
                },
                "membership": {
                    "role": "member",
                    "joined_at": member_data['joined_at'],
                    "joined_via": "invitation"
                }
            },
            meta={
                "redirect": f"/groups/{group_id}",
                "welcome_message": True,
                "first_time_member": True
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
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all invitations for a group with React table data"""
    try:
        db = get_firestore_client()
        
        # Verify admin permissions
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists or member_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Get group info
        group_doc = db.collection('groups').document(group_id).get()
        if not group_doc.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group_doc.to_dict()
        
        # Get all invitations for the group
        invitations_docs = db.collection('invitations').where('group_id', '==', group_id).order_by('created_at', direction='DESCENDING').get()
        
        settings = get_settings()
        invitations = []
        active_count = 0
        expired_count = 0
        used_count = 0
        
        for doc in invitations_docs:
            invitation_data = doc.to_dict()
            
            # Calculate status
            is_expired = datetime.utcnow() > invitation_data['expires_at']
            max_uses = invitation_data.get('max_uses')
            current_uses = invitation_data.get('current_uses', 0)
            is_fully_used = max_uses and current_uses >= max_uses
            is_active = invitation_data.get('is_active', True)
            
            # Determine overall status
            if not is_active:
                status = 'deactivated'
            elif is_expired:
                status = 'expired'
                expired_count += 1
            elif is_fully_used:
                status = 'fully_used'
                used_count += 1
            else:
                status = 'active'
                active_count += 1
            
            # Build invitation URL
            invitation_url = f"{settings.FRONTEND_URL}/join/{invitation_data['token']}"
            
            # Calculate remaining uses
            uses_remaining = None
            if max_uses:
                uses_remaining = max(0, max_uses - current_uses)
            
            # Get creator info
            creator_doc = db.collection('users').document(invitation_data['created_by']).get()
            creator_name = creator_doc.to_dict().get('display_name', 'Unknown') if creator_doc.exists else 'Unknown'
            
            invitation_info = {
                **invitation_data,
                'status': status,
                'invitation_url': invitation_url,
                'uses_remaining': uses_remaining,
                'creator_name': creator_name,
                'is_expired': is_expired,
                'is_fully_used': is_fully_used,
                'can_be_shared': status == 'active'
            }
            
            invitations.append(invitation_info)
        
        return ReactAPIResponse(
            success=True,
            message="Group invitations retrieved",
            data={
                "invitations": invitations,
                "group": {
                    "id": group_id,
                    "name": group_data['name']
                },
                "stats": {
                    "total": len(invitations),
                    "active": active_count,
                    "expired": expired_count,
                    "fully_used": used_count,
                    "deactivated": len(invitations) - active_count - expired_count - used_count
                }
            },
            meta={
                "has_active_invitations": active_count > 0,
                "can_create_more": True
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
    """Deactivate invitation with React confirmation"""
    try:
        db = get_firestore_client()
        
        # Get invitation
        invitation_doc = db.collection('invitations').document(invitation_id).get()
        if not invitation_doc.exists:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        invitation_data = invitation_doc.to_dict()
        
        # Check if user has permission (creator or group admin)
        has_permission = False
        if invitation_data['created_by'] == current_user.uid:
            has_permission = True
        else:
            # Check if user is group admin
            member_doc = db.collection('groups').document(invitation_data['group_id']).collection('members').document(current_user.uid).get()
            if member_doc.exists and member_doc.to_dict().get('role') == 'admin':
                has_permission = True
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Deactivate invitation
        db.collection('invitations').document(invitation_id).update({
            'is_active': False,
            'deactivated_at': datetime.utcnow(),
            'deactivated_by': current_user.uid
        })
        
        return ReactAPIResponse(
            success=True,
            message="Invitation deactivated successfully",
            data={
                "invitation": {
                    "id": invitation_id,
                    "group_name": invitation_data['group_name'],
                    "status": "deactivated"
                }
            },
            meta={
                "action": "invitation_deactivated",
                "requires_refresh": True
            }
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
    """Regenerate invitation token for React security management"""
    try:
        db = get_firestore_client()
        
        # Get invitation
        invitation_doc = db.collection('invitations').document(invitation_id).get()
        if not invitation_doc.exists:
            raise HTTPException(status_code=404, detail="Invitation not found")
        
        invitation_data = invitation_doc.to_dict()
        
        # Check permissions
        has_permission = False
        if invitation_data['created_by'] == current_user.uid:
            has_permission = True
        else:
            member_doc = db.collection('groups').document(invitation_data['group_id']).collection('members').document(current_user.uid).get()
            if member_doc.exists and member_doc.to_dict().get('role') == 'admin':
                has_permission = True
        
        if not has_permission:
            raise HTTPException(status_code=403, detail="Permission denied")
        
        # Generate new token
        new_token = secrets.token_urlsafe(32)
        
        # Update invitation with new token
        db.collection('invitations').document(invitation_id).update({
            'token': new_token,
            'current_uses': 0,  # Reset usage count
            'regenerated_at': datetime.utcnow(),
            'regenerated_by': current_user.uid
        })
        
        settings = get_settings()
        new_invitation_url = f"{settings.FRONTEND_URL}/join/{new_token}"
        
        return ReactAPIResponse(
            success=True,
            message="Invitation token regenerated successfully",
            data={
                "invitation": {
                    "id": invitation_id,
                    "token": new_token,
                    "invitation_url": new_invitation_url,
                    "group_name": invitation_data['group_name'],
                    "uses_reset": True
                }
            },
            meta={
                "new_shareable_link": new_invitation_url,
                "security_action": "token_regenerated"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate invitation: {e}")
        raise HTTPException(status_code=500, detail="Failed to regenerate invitation")

@router.get("/my-invitations", response_model=ReactAPIResponse)
async def get_my_invitations(
    current_user: UserResponse = Depends(get_current_user)
):
    """Get all invitations created by current user for React dashboard"""
    try:
        db = get_firestore_client()
        
        # Get all invitations created by current user
        invitations_docs = db.collection('invitations').where('created_by', '==', current_user.uid).order_by('created_at', direction='DESCENDING').get()
        
        settings = get_settings()
        invitations = []
        
        for doc in invitations_docs:
            invitation_data = doc.to_dict()
            
            # Calculate status
            is_expired = datetime.utcnow() > invitation_data['expires_at']
            max_uses = invitation_data.get('max_uses')
            current_uses = invitation_data.get('current_uses', 0)
            is_fully_used = max_uses and current_uses >= max_uses
            is_active = invitation_data.get('is_active', True)
            
            if not is_active:
                status = 'deactivated'
            elif is_expired:
                status = 'expired'
            elif is_fully_used:
                status = 'fully_used'
            else:
                status = 'active'
            
            invitation_url = f"{settings.FRONTEND_URL}/join/{invitation_data['token']}"
            
            invitations.append({
                **invitation_data,
                'status': status,
                'invitation_url': invitation_url,
                'is_expired': is_expired,
                'is_fully_used': is_fully_used
            })
        
        # Calculate stats
        active_count = len([inv for inv in invitations if inv['status'] == 'active'])
        expired_count = len([inv for inv in invitations if inv['status'] == 'expired'])
        total_uses = sum(inv.get('current_uses', 0) for inv in invitations)
        
        return ReactAPIResponse(
            success=True,
            message="Your invitations retrieved",
            data={
                "invitations": invitations,
                "stats": {
                    "total": len(invitations),
                    "active": active_count,
                    "expired": expired_count,
                    "total_uses": total_uses
                }
            },
            meta={
                "has_invitations": len(invitations) > 0,
                "has_active": active_count > 0
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get user invitations: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve your invitations")

# Helper function for background task
async def send_invitation_emails(
    email_list: List[str], 
    group_name: str, 
    token: str, 
    inviter_name: str,
    invitation_url: str
):
    """Send invitation emails with React-optimized template"""
    try:
        # Create invitation email template
        subject = f"Join {group_name} on Procur - Invitation from {inviter_name}"
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; 
                    line-height: 1.6; 
                    color: #333; 
                    margin: 0; 
                    padding: 0; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    padding: 20px; 
                    background: #ffffff;
                }}
                .header {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 30px 20px; 
                    text-align: center; 
                    border-radius: 8px 8px 0 0;
                }}
                .content {{ 
                    padding: 30px 20px; 
                    background: #f8fafc; 
                    border-radius: 0 0 8px 8px;
                }}
                .button {{ 
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    color: white; 
                    padding: 15px 30px; 
                    text-decoration: none; 
                    border-radius: 6px; 
                    display: inline-block; 
                    font-weight: 600;
                    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
                }}
                .features {{ 
                    background: white; 
                    padding: 20px; 
                    margin: 20px 0; 
                    border-radius: 6px; 
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }}
                .footer {{ 
                    padding: 20px; 
                    text-align: center; 
                    color: #64748b; 
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1 style="margin: 0; font-size: 28px;">🎉 You're Invited!</h1>
                    <p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 18px;">Join {group_name} on Procur</p>
                </div>
                <div class="content">
                    <p style="font-size: 16px; margin-bottom: 20px;">Hi there!</p>
                    <p style="font-size: 16px;"><strong>{inviter_name}</strong> has invited you to join <strong>{group_name}</strong> on Procur, the platform that helps businesses save money through group purchasing power.</p>
                    
                    <div class="features">
                        <h3 style="color: #475569; margin-top: 0;">What you'll get:</h3>
                        <ul style="color: #64748b; padding-left: 20px;">
                            <li>Access to exclusive group discounts from verified suppliers</li>
                            <li>Connect with other businesses in your industry</li>
                            <li>Streamlined procurement process</li>
                            <li>Transparent pricing and bulk buying power</li>
                        </ul>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{invitation_url}" class="button">Join {group_name}</a>
                    </div>
                    
                    <p style="font-size: 14px; color: #64748b; margin-top: 30px;">
                        <strong>Note:</strong> This invitation link will expire in 7 days. 
                        If you're new to Procur, you'll be able to create your account during the join process.
                    </p>
                </div>
                <div class="footer">
                    <p>This invitation was sent by {inviter_name} via Procur</p>
                    <p style="margin: 5px 0;">Questions? Contact our support team</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        You're Invited to Join {group_name} on Procur!
        
        Hi there!
        
        {inviter_name} has invited you to join {group_name} on Procur, the platform that helps businesses save money through group purchasing power.
        
        What you'll get:
        • Access to exclusive group discounts from verified suppliers
        • Connect with other businesses in your industry  
        • Streamlined procurement process
        • Transparent pricing and bulk buying power
        
        Join now: {invitation_url}
        
        Note: This invitation link will expire in 7 days. If you're new to Procur, you'll be able to create your account during the join process.
        
        This invitation was sent by {inviter_name} via Procur
        Questions? Contact our support team
        """
        
        template = EmailTemplate(
            subject=subject,
            html_body=html_body,
            text_body=text_body
        )
        
        # Send emails
        results = await email_service.send_bulk_emails(email_list, template)
        successful_sends = sum(1 for result in results if result is True)
        
        logger.info(f"Sent {successful_sends}/{len(email_list)} invitation emails for group {group_name}")
        
    except Exception as e:
        logger.error(f"Failed to send invitation emails: {e}")

# EOF