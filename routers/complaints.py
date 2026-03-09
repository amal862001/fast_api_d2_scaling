from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from database import get_db
from dependencies import get_current_user, get_complaint_repo
from models.user import PlatformUser
from repositories.complaint_repository import ComplaintRepository
from schemas.complaint_schema import ComplaintSummary, ComplaintDetail, ComplaintCreate, ComplaintUpdate
from services.audit_service import write_audit_log



router = APIRouter(prefix="/complaints", tags=["Complaints"])


# Get all complaints

@router.get("/", response_model=list[ComplaintSummary])
async def get_complaints(
    background_tasks : BackgroundTasks,
    borough          : Optional[str]      = Query(None),
    complaint_type   : Optional[str]      = Query(None),
    status           : Optional[str]      = Query(None),
    start_date       : Optional[datetime] = Query(None),
    end_date         : Optional[datetime] = Query(None),
    page             : int                = Query(1, ge=1),
    limit            : int                = Query(50, le=500),
    repo             : ComplaintRepository = Depends(get_complaint_repo),
    current_user     : PlatformUser        = Depends(get_current_user),
    db               : AsyncSession        = Depends(get_db)
):
    results = await repo.list_paginated(
        agency_code    = current_user.agency_code,
        borough        = borough,
        complaint_type = complaint_type,
        status         = status,
        start_date     = start_date,
        end_date       = end_date,
        page           = page,
        limit          = limit
    )

    # write audit log in background - does not slow down response
    background_tasks.add_task(
        write_audit_log,
        db           = db,
        user_id      = current_user.id,
        agency_code  = current_user.agency_code,
        endpoint     = "/complaints",
        query_params = {
            "borough"        : borough,
            "complaint_type" : complaint_type,
            "status"         : status,
            "start_date"     : str(start_date) if start_date else None,
            "end_date"       : str(end_date) if end_date else None,
            "page"           : page,
            "limit"          : limit
        },
        result_count = len(results)
    )

    return results

# Get single complaint

@router.get("/{unique_key}", response_model=ComplaintDetail)
async def get_complaint(
    unique_key   : int,
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    complaint = await repo.get_by_id(unique_key, current_user.agency_code)

    if complaint is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = "Complaint not found"
        )

    return complaint


# Create complaint

@router.post("/", response_model=ComplaintDetail, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    request      : ComplaintCreate,
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    return await repo.create(
        agency_code    = current_user.agency_code,
        complaint_type = request.complaint_type,
        borough        = request.borough,
        descriptor     = request.descriptor,
        incident_zip   = request.incident_zip,
        city           = request.city,
        location_type  = request.location_type,
        latitude       = request.latitude,
        longitude      = request.longitude
    )


# Update complaint status

@router.patch("/{unique_key}/status", response_model=ComplaintDetail)
async def update_complaint_status(
    unique_key   : int,
    request      : ComplaintUpdate,
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    complaint = await repo.get_by_id(unique_key, current_user.agency_code)

    if complaint is None:
        raise HTTPException(
            status_code = status.HTTP_404_NOT_FOUND,
            detail      = "Complaint not found"
        )

    if request.status:
        complaint.status = request.status

    if request.resolution_description:
        complaint.resolution_description         = request.resolution_description
        complaint.resolution_action_updated_date = datetime.now().replace(tzinfo=None)

    await repo.db.commit()
    await repo.db.refresh(complaint)
    return complaint