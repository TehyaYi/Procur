from procur.core.firebase import get_firestore_client
from procur.models.schemas import (
    GroupCreate, GroupUpdate, GroupResponse, GroupMemberResponse,
    JoinRequestCreate, JoinRequestResponse, JoinRequestUpdate, JoinRequestStatus,
    UserRole, GroupPrivacy
)
from procur.services.email_service import email_service
from procur.templates.email_templates import get_join_request_template, get_join_approved_template
from fastapi import HTTPException
from typing import List, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

class GroupService:
    def __init__(self):
        self._db = None
    
    @property
    def db(self):
        """Lazy initialization of Firestore client"""
        if self._db is None:
            self._db = get_firestore_client()
        return self._db
    
    async def create_group(self, group_data: GroupCreate, admin_uid: str) -> GroupResponse:
        """Create a new group"""
        try:
            group_id = str(uuid.uuid4())
            
            # Prepare group document
            group_doc = {
                **group_data.dict(),
                'id': group_id,
                'admin_id': admin_uid,
                'member_count': 1,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'is_active': True
            }
            
            # Create group document
            self.db.collection('groups').document(group_id).set(group_doc)
            
            # Add admin as first member
            member_data = {
                'user_id': admin_uid,
                'role': UserRole.ADMIN,
                'joined_at': datetime.utcnow()
            }
            self.db.collection('groups').document(group_id).collection('members').document(admin_uid).set(member_data)
            
            return GroupResponse(**group_doc)
            
        except Exception as e:
            logger.error(f"Failed to create group: {e}")
            raise HTTPException(status_code=500, detail="Failed to create group")
    
    async def get_group(self, group_id: str) -> Optional[GroupResponse]:
        """Get group by ID"""
        try:
            group_doc = self.db.collection('groups').document(group_id).get()
            if not group_doc.exists:
                return None
            
            group_data = group_doc.to_dict()
            return GroupResponse(**group_data)
            
        except Exception as e:
            logger.error(f"Failed to get group {group_id}: {e}")
            return None
    
    async def request_to_join(self, request_data: JoinRequestCreate, user_uid: str, user_email: str, user_name: str) -> JoinRequestResponse:
        """Create a join request"""
        try:
            # Check if group exists
            group = await self.get_group(request_data.group_id)
            if not group:
                raise HTTPException(status_code=404, detail="Group not found")
            
            # Check if user is already a member
            member_doc = self.db.collection('groups').document(request_data.group_id).collection('members').document(user_uid).get()
            if member_doc.exists:
                raise HTTPException(status_code=400, detail="Already a member of this group")
            
            # Check if there's already a pending request
            existing_request = self.db.collection('join_requests').where('group_id', '==', request_data.group_id).where('user_id', '==', user_uid).where('status', '==', JoinRequestStatus.PENDING).get()
            if existing_request:
                raise HTTPException(status_code=400, detail="Join request already pending")
            
            # Create join request
            request_id = str(uuid.uuid4())
            join_request = {
                'id': request_id,
                'group_id': request_data.group_id,
                'group_name': group.name,
                'user_id': user_uid,
                'user_email': user_email,
                'user_name': user_name,
                'message': request_data.message,
                'status': JoinRequestStatus.PENDING,
                'created_at': datetime.utcnow()
            }
            
            self.db.collection('join_requests').document(request_id).set(join_request)
            
            # Send email to group admin
            await self._notify_admin_of_join_request(group, join_request)
            
            return JoinRequestResponse(**join_request)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to create join request: {e}")
            raise HTTPException(status_code=500, detail="Failed to create join request")
    
    async def _notify_admin_of_join_request(self, group: GroupResponse, join_request: dict):
        """Send email notification to group admin"""
        try:
            # Get admin email
            admin_doc = self.db.collection('users').document(group.admin_id).get()
            if not admin_doc.exists:
                logger.error(f"Admin user {group.admin_id} not found")
                return
            
            admin_data = admin_doc.to_dict()
            admin_email = admin_data.get('email')
            
            if admin_email:
                template = get_join_request_template(
                    group_name=group.name,
                    requester_name=join_request['user_name'],
                    requester_email=join_request['user_email'],
                    message=join_request.get('message', ''),
                    request_id=join_request['id']
                )
                
                await email_service.send_email(admin_email, template)
                
        except Exception as e:
            logger.error(f"Failed to send admin notification: {e}")

# Create a function to get the service instance
def get_group_service() -> GroupService:
    """Get the group service instance"""
    return GroupService()

# EOF