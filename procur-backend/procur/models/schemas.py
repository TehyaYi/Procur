from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    CURATOR = "curator"

class JoinRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class GroupPrivacy(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    INVITE_ONLY = "invite_only"

# User models
class UserBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    industry: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')
    avatar_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)

class UserCreate(UserBase):
    uid: str = Field(..., min_length=1)

class UserUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    industry: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')

class UserResponse(UserBase):
    uid: str
    created_at: datetime
    updated_at: datetime
    is_active: bool

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    display_name: str = Field(..., min_length=1, max_length=100)
    company_name: Optional[str] = Field(None, max_length=200)
    job_title: Optional[str] = Field(None, max_length=100)
    industry: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=100)
    phone_number: Optional[str] = Field(None, pattern=r'^\+?1?\d{9,15}$')

class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    refresh_token: str

class LogoutResponse(BaseModel):
    success: bool
    message: str
    timestamp: datetime

# Group models
class GroupBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=1000)
    industry: str = Field(..., min_length=2, max_length=100)
    privacy: GroupPrivacy = GroupPrivacy.PUBLIC
    max_members: Optional[int] = Field(None, ge=2, le=10000)
    minimum_order_value: Optional[float] = Field(None, ge=0)
    commission_rate: Optional[float] = Field(None, ge=0, le=1)
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    tags: Optional[List[str]] = Field(None, max_items=10)

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=1000)
    privacy: Optional[GroupPrivacy] = None
    max_members: Optional[int] = Field(None, ge=2, le=10000)
    minimum_order_value: Optional[float] = Field(None, ge=0)
    commission_rate: Optional[float] = Field(None, ge=0, le=1)

class GroupResponse(GroupBase):
    id: str
    admin_id: str
    member_count: int
    created_at: datetime
    updated_at: datetime
    is_active: bool

class GroupMemberResponse(BaseModel):
    user_id: str
    email: str
    display_name: str
    company_name: Optional[str]
    role: UserRole
    joined_at: datetime

# Join request models
class JoinRequestCreate(BaseModel):
    group_id: str = Field(..., min_length=1)
    message: Optional[str] = Field(None, max_length=500)

class JoinRequestResponse(BaseModel):
    id: str
    group_id: str
    group_name: str
    user_id: str
    user_email: str
    user_name: str
    user_company: Optional[str]
    message: Optional[str]
    status: JoinRequestStatus
    created_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None

class JoinRequestUpdate(BaseModel):
    status: JoinRequestStatus
    admin_message: Optional[str] = Field(None, max_length=500)

# Invitation models
class InvitationCreate(BaseModel):
    group_id: str = Field(..., min_length=1)
    expires_in_days: int = Field(7, ge=1, le=365)
    max_uses: Optional[int] = Field(None, ge=1, le=1000)
    email_list: Optional[List[EmailStr]] = Field(None, max_items=100)

class InvitationResponse(BaseModel):
    id: str
    group_id: str
    group_name: str
    token: str
    created_by: str
    expires_at: datetime
    max_uses: Optional[int]
    current_uses: int
    is_active: bool
    created_at: datetime

class InvitationValidateResponse(BaseModel):
    is_valid: bool
    group_id: str
    group_name: str
    group_description: str
    group_industry: str
    expires_at: datetime
    uses_remaining: Optional[int]

# Email templates
class EmailTemplate(BaseModel):
    subject: str
    html_body: str
    text_body: str

# React-specific response models
class ReactAPIResponse(BaseModel):
    """Enhanced API response for React components"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None
    meta: Optional[Dict[str, Any]] = None

class ReactErrorResponse(BaseModel):
    """Standardized error response for React error boundaries"""
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# File upload models
class FileUpload(BaseModel):
    filename: str
    file_type: str
    file_size: int
    upload_url: str

class FileUploadResponse(BaseModel):
    success: bool
    file_info: FileUpload
    cdn_url: Optional[str] = None

# Real-time notification models
class NotificationBase(BaseModel):
    id: str
    user_id: str
    type: str  # 'join_request', 'join_approved', 'group_invitation', etc.
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None
    read: bool = False
    created_at: datetime

class NotificationResponse(NotificationBase):
    pass

# WebSocket message models
class WebSocketMessage(BaseModel):
    type: str  # 'notification', 'group_update', 'member_joined', etc.
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# React component data models
class DashboardData(BaseModel):
    """Data model for React dashboard component"""
    user: UserResponse
    groups: List[GroupResponse]
    recent_notifications: List[NotificationResponse]
    pending_requests: int
    stats: Dict[str, Any]

class GroupDetailData(BaseModel):
    """Data model for React group detail component"""
    group: GroupResponse
    members: List[GroupMemberResponse]
    user_role: Optional[UserRole]
    pending_requests: List[JoinRequestResponse]
    recent_activity: List[Dict[str, Any]]

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    per_page: int
    pages: int
    has_next: bool
    has_prev: bool

# EOF