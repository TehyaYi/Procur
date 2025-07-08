from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from procur.core.dependencies import get_current_user
from procur.models.schemas import UserResponse, FileUploadResponse, ReactAPIResponse
from procur.core.config import get_settings
import os
import uuid
import aiofiles
from typing import Optional
import magic
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

async def validate_file(file: UploadFile, max_size: int, allowed_types: list) -> bool:
    """Validate uploaded file"""
    # Check file size
    content = await file.read()
    await file.seek(0)  # Reset file pointer
    
    if len(content) > max_size:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {max_size/1024/1024}MB")
    
    # Check file type
    mime_type = magic.from_buffer(content, mime=True)
    if mime_type not in allowed_types:
        raise HTTPException(status_code=415, detail=f"File type not allowed. Allowed types: {allowed_types}")
    
    return True

@router.post("/avatar", response_model=FileUploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
):
    """Upload user avatar image"""
    try:
        settings = get_settings()
        
        if not settings.ENABLE_FILE_UPLOADS:
            raise HTTPException(status_code=503, detail="File uploads are disabled")
        
        # Validate file
        await validate_file(file, settings.MAX_FILE_SIZE, settings.ALLOWED_FILE_TYPES)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{current_user.uid}_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, "users", unique_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Build URLs
        upload_url = f"/uploads/users/{unique_filename}"
        cdn_url = f"{settings.CDN_URL}/uploads/users/{unique_filename}" if settings.CDN_URL else upload_url
        
        # Update user avatar in database
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
        db.collection('users').document(current_user.uid).update({
            'avatar_url': cdn_url
        })
        
        return FileUploadResponse(
            success=True,
            file_info={
                "filename": unique_filename,
                "file_type": file.content_type,
                "file_size": len(content),
                "upload_url": upload_url
            },
            cdn_url=cdn_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.post("/group-logo/{group_id}", response_model=FileUploadResponse)
async def upload_group_logo(
    group_id: str,
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user)
):
    """Upload group logo (admin only)"""
    try:
        settings = get_settings()
        
        if not settings.ENABLE_FILE_UPLOADS:
            raise HTTPException(status_code=503, detail="File uploads are disabled")
        
        # Check if user is group admin
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
        
        member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
        if not member_doc.exists or member_doc.to_dict().get('role') != 'admin':
            raise HTTPException(status_code=403, detail="Group admin privileges required")
        
        # Validate file
        await validate_file(file, settings.MAX_FILE_SIZE, settings.ALLOWED_FILE_TYPES)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{group_id}_logo_{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, "groups", unique_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Save file
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Build URLs
        upload_url = f"/uploads/groups/{unique_filename}"
        cdn_url = f"{settings.CDN_URL}/uploads/groups/{unique_filename}" if settings.CDN_URL else upload_url
        
        # Update group logo in database
        db.collection('groups').document(group_id).update({
            'logo_url': cdn_url
        })
        
        return FileUploadResponse(
            success=True,
            file_info={
                "filename": unique_filename,
                "file_type": file.content_type,
                "file_size": len(content),
                "upload_url": upload_url
            },
            cdn_url=cdn_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Group logo upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.delete("/avatar")
async def delete_avatar(current_user: UserResponse = Depends(get_current_user)):
    """Delete user avatar"""
    try:
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
        
        # Get current avatar URL
        user_doc = db.collection('users').document(current_user.uid).get()
        user_data = user_doc.to_dict()
        avatar_url = user_data.get('avatar_url')
        
        if avatar_url:
            # Remove file if it's hosted locally
            if avatar_url.startswith('/uploads/'):
                file_path = avatar_url[1:]  # Remove leading slash
                if os.path.exists(file_path):
                    os.remove(file_path)
            
            # Update database
            db.collection('users').document(current_user.uid).update({
                'avatar_url': None
            })
        
        return ReactAPIResponse(
            success=True,
            message="Avatar deleted successfully"
        )
        
    except Exception as e:
        logger.error(f"Avatar deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Deletion failed")

@router.get("/upload-url")
async def get_upload_url(
    file_type: str,
    file_size: int,
    upload_type: str = "avatar",  # avatar, group_logo, group_banner
    group_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get presigned upload URL for direct file uploads (future S3 integration)"""
    try:
        settings = get_settings()
        
        # Validate file size
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="File too large")
        
        # Validate file type
        if file_type not in settings.ALLOWED_FILE_TYPES:
            raise HTTPException(status_code=415, detail="File type not allowed")
        
        # For now, return upload endpoint (can be enhanced for S3 later)
        upload_endpoint = {
            "avatar": "/api/uploads/avatar",
            "group_logo": f"/api/uploads/group-logo/{group_id}" if group_id else None,
            "group_banner": f"/api/uploads/group-banner/{group_id}" if group_id else None
        }.get(upload_type)
        
        if not upload_endpoint:
            raise HTTPException(status_code=400, detail="Invalid upload type")
        
        return ReactAPIResponse(
            success=True,
            message="Upload URL generated",
            data={
                "upload_url": upload_endpoint,
                "method": "POST",
                "max_file_size": settings.MAX_FILE_SIZE,
                "allowed_types": settings.ALLOWED_FILE_TYPES
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload URL generation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")
