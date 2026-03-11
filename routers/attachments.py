import uuid
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from dependencies import get_current_user, get_complaint_repo
from models.user import PlatformUser
from models.attachment import Attachment
from repositories.complaint_repository import ComplaintRepository

router = APIRouter(tags=["Attachments"])

# where files are stored
UPLOAD_DIR    = "uploads"
MAX_FILE_SIZE = 5 * 1024 * 1024        # 5MB in bytes
ALLOWED_TYPES = {
    "image/jpeg" : ".jpg",
    "image/png"  : ".png",
    "application/pdf" : ".pdf"
}


# Upload attachment

@router.post("/complaints/{unique_key}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    unique_key   : int,
    file         : UploadFile          = File(...),
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
    # ← remove db: AsyncSession = Depends(get_db) entirely
):
    try:
        complaint = await repo.get_by_id(unique_key, current_user.agency_code)
        if complaint is None:
            raise HTTPException(status_code=404, detail="Complaint not found")

        if file.content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=400, detail="File type not allowed")

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large")

        extension   = ALLOWED_TYPES[file.content_type]
        stored_name = f"{uuid.uuid4()}{extension}"
        file_path   = os.path.join(UPLOAD_DIR, stored_name)

        with open(file_path, "wb") as f:
            f.write(contents)

        attachment = Attachment(
            complaint_key = unique_key,
            uploaded_by   = current_user.id,
            agency_code   = current_user.agency_code,
            filename      = file.filename,
            stored_name   = stored_name,
            file_type     = file.content_type,
            file_size     = len(contents)
        )

        repo.db.add(attachment)        # ← repo.db 
        await repo.db.commit()         
        await repo.db.refresh(attachment)  

        return {
            "id"          : attachment.id,
            "filename"    : attachment.filename,
            "file_type"   : attachment.file_type,
            "file_size"   : attachment.file_size,
            "uploaded_at" : attachment.uploaded_at
        }

    except HTTPException:
        raise

    except Exception as e:
        print(f"UPLOAD ERROR: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# List attachments for a complaint

@router.get("/complaints/{unique_key}/attachments")
async def list_attachments(
    unique_key   : int,
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
    # remove db: AsyncSession = Depends(get_db)
):
    complaint = await repo.get_by_id(unique_key, current_user.agency_code)
    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")

    result = await repo.db.execute(    # repo.db
        select(Attachment).where(
            Attachment.complaint_key == unique_key,
            Attachment.agency_code   == current_user.agency_code
        )
    )
    attachments = result.scalars().all()

    return {
        "complaint_key" : unique_key,
        "total"         : len(attachments),
        "attachments"   : [
            {
                "id"          : a.id,
                "filename"    : a.filename,
                "file_type"   : a.file_type,
                "file_size"   : a.file_size,
                "uploaded_at" : a.uploaded_at
            }
            for a in attachments
        ]
    }


# Download attachment

@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id : int,
    repo          : ComplaintRepository = Depends(get_complaint_repo),
    current_user  : PlatformUser        = Depends(get_current_user)
    # ← remove db: AsyncSession = Depends(get_db)
):
    result = await repo.db.execute(    # ← repo.db
        select(Attachment).where(
            Attachment.id          == attachment_id,
            Attachment.agency_code == current_user.agency_code
        )
    )
    attachment = result.scalars().first()

    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = os.path.join(UPLOAD_DIR, attachment.stored_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")

    return FileResponse(
        path       = file_path,
        media_type = attachment.file_type,
        filename   = attachment.filename
    )