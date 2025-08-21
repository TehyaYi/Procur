from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from procur.core.dependencies import (
    get_current_user, get_optional_user, require_group_admin, 
    require_group_member, enforce_group_privacy, get_user_group_role
)
from procur.models.schemas import (
    GroupCreate, GroupUpdate, GroupResponse, GroupMemberResponse,
    JoinRequestCreate, JoinRequestResponse, JoinRequestUpdate,
    UserResponse, ReactAPIResponse, GroupDetailData, PaginatedResponse
)
from procur.services.group_service import get_group_service
from procur.core.firebase import get_firestore_client
from google.cloud.firestore import Increment
from typing import List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/", response_model=ReactAPIResponse)
async def create_group(
    group_data: GroupCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Create a new group (React-friendly response)"""
    try:
        new_group = await get_group_service.create_group(group_data, current_user.uid)
        
        return ReactAPIResponse(
            success=True,
            message=f"Group '{new_group.name}' created successfully",
            data={
                "group": new_group.dict(),
                "user_role": "admin",
                "is_creator": True
            },
            meta={
                "redirect": f"/groups/{new_group.id}",
                "next_steps": [
                    "Add a group logo",
                    "Invite members",
                    "Set up your first purchasing campaign"
                ]
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to create group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=ReactAPIResponse)
async def get_groups(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    industry: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    privacy: Optional[str] = Query(None),
    sort_by: str = Query("created_at", regex="^(created_at|member_count|name)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get list of groups with advanced filtering for React components"""
    try:
        db = get_firestore_client()
        
        # Build base query
        query = db.collection('groups').where('is_active', '==', True)
        
        # Privacy filter - only show public groups for non-authenticated users
        if not current_user:
            query = query.where('privacy', '==', 'public')
        elif privacy:
            query = query.where('privacy', '==', privacy)
        
        # Industry filter
        if industry:
            query = query.where('industry', '==', industry)
        
        # Execute query and get all matching documents
        all_docs = query.get()
        
        # Apply search filter in memory (Firestore doesn't support full-text search)
        filtered_docs = []
        for doc in all_docs:
            group_data = doc.to_dict()
            
            # Search filter
            if search:
                search_lower = search.lower()
                if (search_lower not in group_data['name'].lower() and 
                    search_lower not in group_data['description'].lower() and
                    search_lower not in group_data.get('industry', '').lower()):
                    continue
            
            # Add user-specific data if authenticated
            if current_user:
                member_doc = db.collection('groups').document(doc.id).collection('members').document(current_user.uid).get()
                group_data['is_member'] = member_doc.exists
                group_data['user_role'] = member_doc.to_dict().get('role') if member_doc.exists else None
                
                # Check if there's a pending join request
                pending_request = db.collection('join_requests').where('group_id', '==', doc.id).where('user_id', '==', current_user.uid).where('status', '==', 'pending').get()
                group_data['has_pending_request'] = len(pending_request) > 0
            else:
                group_data['is_member'] = False
                group_data['user_role'] = None
                group_data['has_pending_request'] = False
            
            filtered_docs.append(group_data)
        
        # Apply sorting
        if sort_by == 'name':
            filtered_docs.sort(key=lambda x: x['name'].lower(), reverse=(sort_order == 'desc'))
        elif sort_by == 'member_count':
            filtered_docs.sort(key=lambda x: x.get('member_count', 0), reverse=(sort_order == 'desc'))
        else:  # created_at
            filtered_docs.sort(key=lambda x: x['created_at'], reverse=(sort_order == 'desc'))
        
        # Apply pagination
        total = len(filtered_docs)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_groups = filtered_docs[start_idx:end_idx]
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        return ReactAPIResponse(
            success=True,
            message="Groups retrieved successfully",
            data={
                "groups": paginated_groups,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get groups: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve groups")

@router.get("/{group_id}", response_model=ReactAPIResponse)
async def get_group_detail(
    group_id: str,
    current_user: Optional[UserResponse] = Depends(get_optional_user)
):
    """Get detailed group information for React group page"""
    try:
        # Enforce group privacy settings
        await enforce_group_privacy(group_id, current_user)
        
        db = get_firestore_client()
        
        # Get group
        group_doc = db.collection('groups').document(group_id).get()
        if not group_doc.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group_doc.to_dict()
        
        # Get user's relationship to group
        user_role = None
        is_member = False
        has_pending_request = False
        can_join = True
        
        if current_user:
            # Check membership
            member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
            if member_doc.exists:
                is_member = True
                user_role = member_doc.to_dict().get('role')
                can_join = False
            else:
                # Check for pending join request
                pending_requests = db.collection('join_requests').where('group_id', '==', group_id).where('user_id', '==', current_user.uid).where('status', '==', 'pending').get()
                has_pending_request = len(pending_requests) > 0
                can_join = not has_pending_request
        
        # Get members (limited for non-members)
        members = []
        if is_member or group_data['privacy'] == 'public':
            members_ref = db.collection('groups').document(group_id).collection('members')
            if not is_member:
                # Non-members see only first 5 members
                members_docs = members_ref.limit(5).get()
            else:
                members_docs = members_ref.get()
            
            for member_doc in members_docs:
                member_data = member_doc.to_dict()
                user_doc = db.collection('users').document(member_data['user_id']).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    members.append({
                        "user_id": member_data['user_id'],
                        "email": user_data['email'],
                        "display_name": user_data['display_name'],
                        "company_name": user_data.get('company_name'),
                        "avatar_url": user_data.get('avatar_url'),
                        "role": member_data['role'],
                        "joined_at": member_data['joined_at']
                    })
        
        # Get pending join requests (admin only)
        pending_requests = []
        if user_role == 'admin':
            requests_docs = db.collection('join_requests').where('group_id', '==', group_id).where('status', '==', 'pending').order_by('created_at', direction='DESCENDING').get()
            
            for req_doc in requests_docs:
                req_data = req_doc.to_dict()
                # Get requester details
                user_doc = db.collection('users').document(req_data['user_id']).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    req_data['user_company'] = user_data.get('company_name')
                    req_data['user_avatar'] = user_data.get('avatar_url')
                
                pending_requests.append(req_data)
        
        # Get recent activity (placeholder for future implementation)
        recent_activity = []
        
        # Add user-specific data to group
        group_data.update({
            'is_member': is_member,
            'user_role': user_role,
            'has_pending_request': has_pending_request,
            'can_join': can_join,
            'can_manage': user_role == 'admin'
        })
        
        return ReactAPIResponse(
            success=True,
            message="Group details retrieved",
            data={
                "group": group_data,
                "members": members,
                "pending_requests": pending_requests,
                "recent_activity": recent_activity,
                "user_context": {
                    "is_member": is_member,
                    "user_role": user_role,
                    "has_pending_request": has_pending_request,
                    "can_join": can_join,
                    "can_manage": user_role == 'admin'
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get group detail: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve group details")

@router.put("/{group_id}", response_model=ReactAPIResponse)
async def update_group(
    group_id: str,
    group_update: GroupUpdate,
    current_user: UserResponse = Depends(require_group_admin)
):
    """Update group (admin only)"""
    try:
        updated_group = await get_group_service.update_group(group_id, group_update, current_user.uid)
        
        return ReactAPIResponse(
            success=True,
            message=f"Group '{updated_group.name}' updated successfully",
            data={"group": updated_group.dict()}
        )
        
    except Exception as e:
        logger.error(f"Failed to update group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{group_id}", response_model=ReactAPIResponse)
async def delete_group(
    group_id: str,
    current_user: UserResponse = Depends(require_group_admin)
):
    """Delete group (admin only)"""
    try:
        await get_group_service.delete_group(group_id, current_user.uid)
        
        return ReactAPIResponse(
            success=True,
            message="Group deleted successfully",
            meta={"redirect": "/groups"}
        )
        
    except Exception as e:
        logger.error(f"Failed to delete group: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{group_id}/join", response_model=ReactAPIResponse)
async def request_join_group(
    group_id: str,
    join_request: JoinRequestCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Request to join a group"""
    try:
        db = get_firestore_client()
        
        # First, verify the group exists and is active
        group_doc = db.collection('groups').document(group_id).get()
        if not group_doc.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group_doc.to_dict()
        if not group_data.get('is_active', True):
            raise HTTPException(status_code=400, detail="Group is not accepting new members")
        
        # Check if user is already a member
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if member_doc.exists:
            raise HTTPException(status_code=400, detail="Already a member of this group")
        
        # Check if there's already a pending request
        existing_requests = db.collection('join_requests').where('group_id', '==', group_id).where('user_id', '==', current_user.uid).where('status', '==', 'pending').get()
        if len(existing_requests) > 0:
            raise HTTPException(status_code=400, detail="Join request already pending")
        
        # Create join request
        request_data = {
            'group_id': group_id,
            'user_id': current_user.uid,
            'message': join_request.message,
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        # Add to join_requests collection
        request_ref = db.collection('join_requests').add(request_data)
        request_id = request_ref[1].id
        
        # Get group details for notification
        group_doc = db.collection('groups').document(group_id).get()
        group_data = group_doc.to_dict()
        
        # Notify group admins (background task)
        # This would typically be handled by a background job system
        
        return ReactAPIResponse(
            success=True,
            message=f"Join request sent to '{group_data['name']}'",
            data={
                "request_id": request_id,
                "group_name": group_data['name']
            },
            meta={
                "next_steps": [
                    "Wait for admin approval",
                    "Check your email for updates"
                ]
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create join request: {e}")
        raise HTTPException(status_code=500, detail="Failed to send join request")

@router.get("/{group_id}/join-requests", response_model=ReactAPIResponse)
async def get_join_requests(
    group_id: str,
    status: Optional[str] = Query(None),
    current_user: UserResponse = Depends(require_group_admin)
):
    """Get join requests for a group (admin only)"""
    try:
        db = get_firestore_client()
        
        # Build query
        query = db.collection('join_requests').where('group_id', '==', group_id)
        if status:
            query = query.where('status', '==', status)
        
        # Get requests
        requests_docs = query.order_by('created_at', direction='DESCENDING').get()
        
        # Build response
        requests = []
        for req_doc in requests_docs:
            req_data = req_doc.to_dict()
            
            # Get requester details
            user_doc = db.collection('users').document(req_data['user_id']).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                req_data['user_email'] = user_data['email']
                req_data['user_name'] = user_data['display_name']
                req_data['user_company'] = user_data.get('company_name')
                req_data['user_avatar'] = user_data.get('avatar_url')
            
            requests.append(req_data)
        
        return ReactAPIResponse(
            success=True,
            message="Join requests retrieved",
            data={"requests": requests}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get join requests: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve join requests")

@router.patch("/join-requests/{request_id}", response_model=ReactAPIResponse)
async def handle_join_request(
    request_id: str,
    request_update: JoinRequestUpdate,
    background_tasks: BackgroundTasks,
    current_user: UserResponse = Depends(get_current_user)
):
    """Handle join request (approve/reject) - admin only"""
    try:
        db = get_firestore_client()
        
        # Get the join request
        request_doc = db.collection('join_requests').document(request_id).get()
        if not request_doc.exists:
            raise HTTPException(status_code=404, detail="Join request not found")
        
        request_data = request_doc.to_dict()
        group_id = request_data['group_id']
        
        # Verify admin privileges by checking group membership directly
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        
        if not member_doc.exists:
            raise HTTPException(status_code=403, detail="Not a member of this group")
        
        member_data = member_doc.to_dict()
        if member_data.get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Update request status
        update_data = {
            'status': request_update.status,
            'reviewed_at': datetime.utcnow(),
            'reviewed_by': current_user.uid,
            'admin_message': request_update.admin_message,
            'updated_at': datetime.utcnow()
        }
        
        db.collection('join_requests').document(request_id).update(update_data)
        
        # If approved, add user to group
        if request_update.status == 'approved':
            # Add user to group members
            member_data = {
                'user_id': request_data['user_id'],
                'role': 'member',
                'joined_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            
            db.collection('groups').document(group_id).collection('members').document(request_data['user_id']).set(member_data)
            
            # Increment member count
            db.collection('groups').document(group_id).update({
                'member_count': Increment(1)
            })
            
            # Send approval email
            background_tasks.add_task(send_approval_email, request_data['user_id'], group_id)
        
        return ReactAPIResponse(
            success=True,
            message=f"Join request {request_update.status}",
            data={"request_id": request_id, "status": request_update.status}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to handle join request: {e}")
        raise HTTPException(status_code=500, detail="Failed to process join request")

@router.get("/{group_id}/members", response_model=ReactAPIResponse)
async def get_group_members(
    group_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: UserResponse = Depends(require_group_member)
):
    """Get group members with pagination (members only)"""
    try:
        db = get_firestore_client()
        
        # Get all members
        members_ref = db.collection('groups').document(group_id).collection('members')
        all_members_docs = members_ref.get()
        
        # Build member list with user details
        all_members = []
        for member_doc in all_members_docs:
            member_data = member_doc.to_dict()
            
            # Get user details
            user_doc = db.collection('users').document(member_data['user_id']).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                all_members.append({
                    "user_id": member_data['user_id'],
                    "email": user_data['email'],
                    "display_name": user_data['display_name'],
                    "company_name": user_data.get('company_name'),
                    "avatar_url": user_data.get('avatar_url'),
                    "bio": user_data.get('bio'),
                    "role": member_data['role'],
                    "joined_at": member_data['joined_at'],
                    "is_current_user": member_data['user_id'] == current_user.uid
                })
        
        # Sort by role (admins first) then by join date
        all_members.sort(key=lambda x: (x['role'] != 'admin', x['joined_at']))
        
        # Apply pagination
        total = len(all_members)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_members = all_members[start_idx:end_idx]
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        # Calculate member stats
        admin_count = len([m for m in all_members if m['role'] == 'admin'])
        member_count = len([m for m in all_members if m['role'] == 'member'])
        
        return ReactAPIResponse(
            success=True,
            message="Group members retrieved",
            data={
                "members": paginated_members,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": has_next,
                    "has_prev": has_prev
                },
                "stats": {
                    "total_members": total,
                    "admins": admin_count,
                    "members": member_count
                }
            },
            meta={
                "user_role": await get_user_group_role(group_id, current_user),
                "can_manage": await get_user_group_role(group_id, current_user) == 'admin'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get group members: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve group members")

@router.delete("/{group_id}/members/{user_id}", response_model=ReactAPIResponse)
async def remove_member(
    group_id: str,
    user_id: str,
    current_user: UserResponse = Depends(require_group_admin)
):
    """Remove member from group (admin only)"""
    try:
        db = get_firestore_client()
        
        # Prevent admin from removing themselves
        if user_id == current_user.uid:
            raise HTTPException(status_code=400, detail="Cannot remove yourself from admin role")
        
        # Check if user is actually a member
        member_doc = db.collection('groups').document(group_id).collection('members').document(user_id).get()
        if not member_doc.exists:
            raise HTTPException(status_code=404, detail="User is not a member of this group")
        
        # Remove member
        db.collection('groups').document(group_id).collection('members').document(user_id).delete()
        
        # Decrement member count
        db.collection('groups').document(group_id).update({
            'member_count': Increment(-1)
        })
        
        return ReactAPIResponse(
            success=True,
            message="Member removed from group",
            data={"removed_user_id": user_id}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove member")

@router.post("/{group_id}/leave", response_model=ReactAPIResponse)
async def leave_group(
    group_id: str,
    current_user: UserResponse = Depends(require_group_member)
):
    """Leave a group"""
    try:
        db = get_firestore_client()
        
        # Check if user is the only admin
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        member_data = member_doc.to_dict()
        
        if member_data.get('role') == 'admin':
            # Check if there are other admins
            admin_members = db.collection('groups').document(group_id).collection('members').where('role', '==', 'admin').get()
            if len(admin_members) <= 1:
                raise HTTPException(status_code=400, detail="Cannot leave group as the only admin. Transfer admin role first or delete the group.")
        
        # Remove user from group
        db.collection('groups').document(group_id).collection('members').document(current_user.uid).delete()
        
        # Decrement member count
        db.collection('groups').document(group_id).update({
            'member_count': Increment(-1)
        })
        
        return ReactAPIResponse(
            success=True,
            message="Successfully left the group",
            meta={"redirect": "/groups"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to leave group: {e}")
        raise HTTPException(status_code=500, detail="Failed to leave group")

# Helper function for sending approval emails
async def send_approval_email(user_id: str, group_id: str):
    """Send approval email to user (placeholder for email service integration)"""
    try:
        # This would integrate with your email service
        logger.info(f"Approval email sent to user {user_id} for group {group_id}")
    except Exception as e:
        logger.error(f"Failed to send approval email: {e}")