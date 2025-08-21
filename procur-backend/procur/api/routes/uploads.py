from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from procur.core.dependencies import get_current_user, require_group_admin
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
    current_user: UserResponse = Depends(require_group_admin)
):
    """Upload group logo (admin only)"""
    try:
        settings = get_settings()
        
        if not settings.ENABLE_FILE_UPLOADS:
            raise HTTPException(status_code=503, detail="File uploads are disabled")
        
        # Validate file
        await validate_file(file, settings.MAX_FILE_SIZE, settings.ALLOWED_FILE_TYPES)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"group_{group_id}_{uuid.uuid4()}{file_extension}"
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
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
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

@router.post("/group-banner/{group_id}", response_model=FileUploadResponse)
async def upload_group_banner(
    group_id: str,
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(require_group_admin)
):
    """Upload group banner image (admin only)"""
    try:
        settings = get_settings()
        
        if not settings.ENABLE_FILE_UPLOADS:
            raise HTTPException(status_code=503, detail="File uploads are disabled")
        
        # Validate file
        await validate_file(file, settings.MAX_FILE_SIZE, settings.ALLOWED_FILE_TYPES)
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"banner_{group_id}_{uuid.uuid4()}{file_extension}"
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
        
        # Update group banner in database
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
        db.collection('groups').document(group_id).update({
            'banner_url': cdn_url
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
        logger.error(f"Group banner upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@router.delete("/avatar")
async def delete_avatar(current_user: UserResponse = Depends(get_current_user)):
    """Delete user avatar"""
    try:
        settings = get_settings()
        
        if not settings.ENABLE_FILE_UPLOADS:
            raise HTTPException(status_code=503, detail="File uploads are disabled")
        
        # Get current avatar URL
        from procur.core.firebase import get_firestore_client
        db = get_firestore_client()
        user_doc = db.collection('users').document(current_user.uid).get()
        
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_data = user_doc.to_dict()
        current_avatar = user_data.get('avatar_url')
        
        if not current_avatar:
            return ReactAPIResponse(
                success=True,
                message="No avatar to delete",
                data={"avatar_deleted": False}
            )
        
        # Remove avatar from database
        db.collection('users').document(current_user.uid).update({
            'avatar_url': None
        })
        
        # Try to delete file if it's a local upload
        if current_avatar.startswith('/uploads/'):
            try:
                file_path = os.path.join(settings.UPLOAD_DIR, current_avatar.lstrip('/uploads/'))
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted avatar file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete avatar file: {e}")
        
        return ReactAPIResponse(
            success=True,
            message="Avatar deleted successfully",
            data={"avatar_deleted": True}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Avatar deletion failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete avatar")

@router.get("/upload-url")
async def get_upload_url(
    file_type: str,
    file_size: int,
    upload_type: str = "avatar",  # avatar, group_logo, group_banner
    group_id: Optional[str] = None,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get pre-signed upload URL for direct file uploads"""
    try:
        settings = get_settings()
        
        if not settings.ENABLE_FILE_UPLOADS:
            raise HTTPException(status_code=503, detail="File uploads are disabled")
        
        # Validate file size
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large. Max size: {settings.MAX_FILE_SIZE/1024/1024}MB")
        
        # Validate upload type
        if upload_type not in ["avatar", "group_logo", "group_banner"]:
            raise HTTPException(status_code=400, detail="Invalid upload type")
        
        # For group uploads, verify admin permissions
        if upload_type in ["group_logo", "group_banner"] and group_id:
            # Verify admin privileges by checking group membership directly
            from procur.core.firebase import get_firestore_client
            db = get_firestore_client()
            member_doc = db.collection('groups').document(group_id).collection('members').document(current_user.uid).get()
            
            if not member_doc.exists:
                raise HTTPException(status_code=403, detail="Not a member of this group")
            
            member_data = member_doc.to_dict()
            if member_data.get('role') != 'admin':
                raise HTTPException(status_code=403, detail="Admin privileges required")
        
        # Generate unique filename
        file_extension = f".{file_type}"
        if upload_type == "avatar":
            unique_filename = f"{current_user.uid}_{uuid.uuid4()}{file_extension}"
        else:
            unique_filename = f"{upload_type}_{group_id}_{uuid.uuid4()}{file_extension}"
        
        # Build file path
        if upload_type == "avatar":
            file_path = f"users/{unique_filename}"
        else:
            file_path = f"groups/{unique_filename}"
        
        # For now, return the file path (in production, you'd generate a pre-signed URL)
        upload_url = f"/uploads/{file_path}"
        
        return ReactAPIResponse(
            success=True,
            message="Upload URL generated",
            data={
                "upload_url": upload_url,
                "filename": unique_filename,
                "file_path": file_path,
                "expires_in": 3600  # 1 hour
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate upload URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate upload URL")
