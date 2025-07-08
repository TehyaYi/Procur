from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from procur.core.dependencies import get_current_user, get_optional_user
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
        
        # Sort results
        reverse_order = sort_order == "desc"
        if sort_by == "name":
            filtered_docs.sort(key=lambda x: x['name'].lower(), reverse=reverse_order)
        elif sort_by == "member_count":
            filtered_docs.sort(key=lambda x: x.get('member_count', 0), reverse=reverse_order)
        else:  # created_at
            filtered_docs.sort(key=lambda x: x.get('created_at', datetime.min), reverse=reverse_order)
        
        # Calculate pagination
        total = len(filtered_docs)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_groups = filtered_docs[start_idx:end_idx]
        
        # Calculate pagination metadata
        total_pages = (total + per_page - 1) // per_page
        has_next = page < total_pages
        has_prev = page > 1
        
        # Get available industries for filter dropdown
        available_industries = list(set(doc.get('industry') for doc in all_docs if doc.get('industry')))
        available_industries.sort()
        
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
                },
                "filters": {
                    "available_industries": available_industries,
                    "applied_filters": {
                        "industry": industry,
                        "search": search,
                        "privacy": privacy,
                        "sort_by": sort_by,
                        "sort_order": sort_order
                    }
                }
            },
            meta={
                "total_groups": total,
                "authenticated": current_user is not None,
                "page_info": f"Page {page} of {total_pages}"
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
        db = get_firestore_client()
        
        # Get group
        group_doc = db.collection('groups').document(group_id).get()
        if not group_doc.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group_doc.to_dict()
        
        # Check privacy settings
        if group_data['privacy'] != 'public' and not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")
        
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
                "stats": {
                    "total_members": len(members) if is_member else group_data.get('member_count', 0),
                    "pending_requests_count": len(pending_requests),
                    "admin_count": len([m for m in members if m.get('role') == 'admin'])
                }
            },
            meta={
                "user_permissions": {
                    "can_view_members": is_member or group_data['privacy'] == 'public',
                    "can_manage_group": user_role == 'admin',
                    "can_invite": is_member,
                    "can_leave": is_member and user_role != 'admin'
                },
                "group_status": {
                    "is_full": group_data.get('max_members') and group_data.get('member_count', 0) >= group_data['max_members'],
                    "accepting_members": group_data['privacy'] != 'invite_only' or is_member
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
    current_user: UserResponse = Depends(get_current_user)
):
    """Update group (admin only) with React form validation"""
    try:
        db = get_firestore_client()
        
        # Verify admin permissions
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists or member_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Get current group
        group_doc = db.collection('groups').document(group_id).get()
        if not group_doc.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        # Prepare update data
        update_data = {k: v for k, v in group_update.dict().items() if v is not None}
        if update_data:
            update_data['updated_at'] = datetime.utcnow()
            
            # Update group document
            db.collection('groups').document(group_id).update(update_data)
            
            # Get updated group data
            updated_doc = db.collection('groups').document(group_id).get()
            updated_group = updated_doc.to_dict()
            
            return ReactAPIResponse(
                success=True,
                message="Group updated successfully",
                data={
                    "group": updated_group,
                    "updated_fields": list(update_data.keys())
                },
                meta={
                    "last_updated": update_data['updated_at'].isoformat(),
                    "updated_by": current_user.uid
                }
            )
        else:
            return ReactAPIResponse(
                success=False,
                message="No fields to update",
                data={"group": group_doc.to_dict()}
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update group {group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update group")

@router.delete("/{group_id}", response_model=ReactAPIResponse)
async def delete_group(
    group_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Delete group (admin only) with confirmation for React"""
    try:
        db = get_firestore_client()
        
        # Verify admin permissions
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists or member_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Get group info for confirmation
        group_doc = db.collection('groups').document(group_id).get()
        if not group_doc.exists:
            raise HTTPException(status_code=404, detail="Group not found")
        
        group_data = group_doc.to_dict()
        
        # Soft delete - mark as inactive
        db.collection('groups').document(group_id).update({
            'is_active': False,
            'deleted_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        })
        
        return ReactAPIResponse(
            success=True,
            message=f"Group '{group_data['name']}' deleted successfully",
            data={
                "deleted_group": {
                    "id": group_id,
                    "name": group_data['name'],
                    "member_count": group_data.get('member_count', 0)
                }
            },
            meta={
                "redirect": "/dashboard",
                "action": "group_deleted"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete group {group_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete group")

@router.post("/{group_id}/join", response_model=ReactAPIResponse)
async def request_join_group(
    group_id: str,
    join_request: JoinRequestCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """Request to join a group with React form handling"""
    try:
        join_request.group_id = group_id  # Ensure consistency
        
        request_response = await get_group_service.request_to_join(
            join_request, 
            current_user.uid, 
            current_user.email, 
            current_user.display_name
        )
        
        return ReactAPIResponse(
            success=True,
            message="Join request submitted successfully",
            data={
                "join_request": request_response.dict(),
                "status": "pending"
            },
            meta={
                "next_step": "wait_for_approval",
                "notification_sent": True
            }
        )
        
    except HTTPException as e:
        return ReactAPIResponse(
            success=False,
            message=str(e.detail),
            data={"error_code": "JOIN_REQUEST_FAILED"}
        )
    except Exception as e:
        logger.error(f"Join request failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to submit join request")

@router.get("/{group_id}/join-requests", response_model=ReactAPIResponse)
async def get_join_requests(
    group_id: str,
    status: Optional[str] = Query(None),
    current_user: UserResponse = Depends(get_current_user)
):
    """Get join requests for group (admin only) with React table data"""
    try:
        db = get_firestore_client()
        
        # Verify admin permissions
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists or member_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Build query
        query = db.collection('join_requests').where('group_id', '==', group_id)
        if status:
            query = query.where('status', '==', status)
        
        # Execute query
        requests_docs = query.order_by('created_at', direction='DESCENDING').get()
        
        requests = []
        for doc in requests_docs:
            request_data = doc.to_dict()
            
            # Get additional user info
            user_doc = db.collection('users').document(request_data['user_id']).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                request_data['user_company'] = user_data.get('company_name')
                request_data['user_avatar'] = user_data.get('avatar_url')
                request_data['user_bio'] = user_data.get('bio')
            
            requests.append(request_data)
        
        # Calculate stats
        pending_count = len([r for r in requests if r['status'] == 'pending'])
        approved_count = len([r for r in requests if r['status'] == 'approved'])
        rejected_count = len([r for r in requests if r['status'] == 'rejected'])
        
        return ReactAPIResponse(
            success=True,
            message="Join requests retrieved",
            data={
                "requests": requests,
                "stats": {
                    "total": len(requests),
                    "pending": pending_count,
                    "approved": approved_count,
                    "rejected": rejected_count
                }
            },
            meta={
                "has_pending": pending_count > 0,
                "filter_applied": status is not None
            }
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
    """Approve or reject join request with React notifications"""
    try:
        db = get_firestore_client()
        
        # Get join request
        request_doc = db.collection('join_requests').document(request_id).get()
        if not request_doc.exists:
            raise HTTPException(status_code=404, detail="Join request not found")
        
        request_data = request_doc.to_dict()
        
        # Verify user is admin of the group
        member_doc = db.collection('groups').document(request_data['group_id']).collection('members').document(current_user.uid).get()
        if not member_doc.exists or member_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Update request status
        update_data = {
            'status': request_update.status,
            'reviewed_at': datetime.utcnow(),
            'reviewed_by': current_user.uid,
            'admin_message': request_update.admin_message
        }
        
        db.collection('join_requests').document(request_id).update(update_data)
        
        # If approved, add user to group
        if request_update.status == 'approved':
            # Add user as member
            member_data = {
                'user_id': request_data['user_id'],
                'role': 'member',
                'joined_at': datetime.utcnow()
            }
            db.collection('groups').document(request_data['group_id']).collection('members').document(request_data['user_id']).set(member_data)
            
            # Update group member count
            group_ref = db.collection('groups').document(request_data['group_id'])
            group_ref.update({'member_count': Increment(1)})
            
            # Send approval email
            background_tasks.add_task(
                send_approval_email,
                request_data['user_email'],
                request_data['user_name'],
                request_data['group_name']
            )
            
            action_message = f"{request_data['user_name']} has been added to the group"
        else:
            action_message = f"Join request from {request_data['user_name']} has been rejected"
        
        # Get updated request
        updated_doc = db.collection('join_requests').document(request_id).get()
        updated_data = updated_doc.to_dict()
        
        return ReactAPIResponse(
            success=True,
            message=action_message,
            data={
                "join_request": updated_data,
                "action": request_update.status
            },
            meta={
                "member_added": request_update.status == 'approved',
                "notification_sent": True
            }
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
    current_user: UserResponse = Depends(get_current_user)
):
    """Get group members with pagination for React components"""
    try:
        db = get_firestore_client()
        
        # Verify user is member of the group
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists:
            raise HTTPException(status_code=403, detail="Must be a group member to view members")
        
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
                "user_role": member_doc.to_dict().get('role'),
                "can_manage": member_doc.to_dict().get('role') == 'admin'
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
    current_user: UserResponse = Depends(get_current_user)
):
    """Remove member from group (admin only) with React confirmation"""
    try:
        db = get_firestore_client()
        
        # Verify admin permissions
        admin_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not admin_doc.exists or admin_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Cannot remove admin (self)
        if user_id == current_user.uid:
            return ReactAPIResponse(
                success=False,
                message="Cannot remove yourself as group admin",
                data={"error_code": "CANNOT_REMOVE_ADMIN"}
            )
        
        # Check if user is member
        member_doc = db.collection('groups').document(group_id).collection('members').document(user_id).get()
        if not member_doc.exists:
            raise HTTPException(status_code=404, detail="User is not a member of this group")
        
        # Get user info for response
        user_doc = db.collection('users').document(user_id).get()
        user_name = user_doc.to_dict().get('display_name', 'Unknown User') if user_doc.exists else 'Unknown User'
        
        # Remove member
        db.collection('groups').document(group_id).collection('members').document(user_id).delete()
        
        # Update group member count
        group_ref = db.collection('groups').document(group_id)
        group_ref.update({'member_count': Increment(-1)})
        
        return ReactAPIResponse(
            success=True,
            message=f"{user_name} has been removed from the group",
            data={
                "removed_user": {
                    "user_id": user_id,
                    "name": user_name
                }
            },
            meta={
                "action": "member_removed",
                "requires_refresh": True
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove member: {e}")
        raise HTTPException(status_code=500, detail="Failed to remove member")

@router.post("/{group_id}/leave", response_model=ReactAPIResponse)
async def leave_group(
    group_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Leave group with React confirmation flow"""
    try:
        db = get_firestore_client()
        
        # Check if user is member
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists:
            raise HTTPException(status_code=404, detail="Not a member of this group")
        
        member_data = member_doc.to_dict()
        
        # Check if user is admin
        if member_data.get('role') == 'admin':
            return ReactAPIResponse(
                success=False,
                message="Group admin cannot leave. Transfer admin privileges first.",
                data={
                    "error_code": "ADMIN_CANNOT_LEAVE",
                    "required_action": "transfer_admin"
                },
                meta={
                    "next_step": "transfer_admin_rights"
                }
            )
        
        # Get group info for response
        group_doc = db.collection('groups').document(group_id).get()
        group_name = group_doc.to_dict().get('name', 'Unknown Group') if group_doc.exists else 'Unknown Group'
        
        # Remove member
        db.collection('groups').document(group_id).collection('members').document(current_user.uid).delete()
        
        # Update group member count
        group_ref = db.collection('groups').document(group_id)
        group_ref.update({'member_count': Increment(-1)})
        
        return ReactAPIResponse(
            success=True,
            message=f"You have left {group_name}",
            data={
                "left_group": {
                    "group_id": group_id,
                    "group_name": group_name
                }
            },
            meta={
                "redirect": "/dashboard",
                "action": "left_group"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to leave group: {e}")
        raise HTTPException(status_code=500, detail="Failed to leave group")

# Helper function for background task
async def send_approval_email(user_email: str, user_name: str, group_name: str):
   """Send approval email notification"""
   try:
       from procur.services.email_service import email_service
       from procur.templates.email_templates import get_join_approved_template
       
       template = get_join_approved_template(group_name, user_name)
       await email_service.send_email(user_email, template)
       
   except Exception as e:
       logger.error(f"Failed to send approval email: {e}")

# EOF