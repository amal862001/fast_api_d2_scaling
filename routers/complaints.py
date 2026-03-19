from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from database import get_db
from dependencies import get_current_user, get_complaint_repo, require_scope
from models.user import PlatformUser
from repositories.complaint_repository import ComplaintRepository
from schemas.complaint_schema import ComplaintSummary, ComplaintDetail, ComplaintCreate, ComplaintUpdate
from services.audit_service import write_audit_log

from services.cache_service import (
    cache_get, cache_set, cache_delete_pattern,
    key_complaints
)

from fastapi.responses import StreamingResponse
from datetime import date
import csv
import io




router = APIRouter(prefix="/complaints", tags=["Complaints"])


# Get all complaints

# GET /complaints — TTL 60s

@router.get("/", response_model=list[ComplaintSummary])
async def get_complaints(
    response         : Response,
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
    filters = {
        "borough"        : borough,
        "complaint_type" : complaint_type,
        "status"         : status,
        "start_date"     : str(start_date) if start_date else None,
        "end_date"       : str(end_date) if end_date else None,
        "page"           : page,
        "limit"          : limit
    }

    key    = key_complaints(current_user.agency_code, filters)
    cached = await cache_get(key, endpoint="complaints")

    if cached:
        response.headers["X-Cache"] = "HIT"
        return cached

    results = await repo.list_paginated(
        agency_code    = current_user.agency_code,
        **{k: v for k, v in filters.items() if k not in ("start_date", "end_date")},
        start_date     = start_date,
        end_date       = end_date,
    )

    # serialize for cache — convert SQLAlchemy objects to dicts
    serialized = [
        {
            "unique_key"     : r.unique_key,
            "created_date"   : str(r.created_date),
            "complaint_type" : r.complaint_type,
            "descriptor"     : r.descriptor,
            "borough"        : r.borough,
            "status"         : r.status,
            "agency"         : r.agency,
            "incident_zip"   : r.incident_zip
        }
        for r in results
    ]

    await cache_set(key, serialized, ttl_seconds=60)
    response.headers["X-Cache"] = "MISS"

    background_tasks.add_task(
        write_audit_log,
        db           = db,
        user_id      = current_user.id,
        agency_code  = current_user.agency_code,
        endpoint     = "/complaints",
        query_params = filters,
        result_count = len(results)
    )

    return serialized



# Export complaints as CSV — stream response, invalidate cache

@router.get("/export")
async def export_complaints(
    borough        : Optional[str]      = Query(None),
    complaint_type : Optional[str]      = Query(None),
    status         : Optional[str]      = Query(None),
    start_date     : Optional[datetime] = Query(None),
    end_date       : Optional[datetime] = Query(None),
    repo           : ComplaintRepository = Depends(get_complaint_repo),
    current_user   : PlatformUser        = Depends(require_scope("complaints:export"))
):
    # CSV generator
    async def csv_generator():
        # yield header row first
        header = [
            "unique_key", "created_date", "closed_date",
            "agency", "agency_name", "complaint_type",
            "descriptor", "location_type", "incident_zip",
            "city", "borough", "status",
            "resolution_description", "latitude",
            "longitude", "resolution_action_updated_date"
        ]
        yield ",".join(header) + "\n"

        # stream rows in batches of 500
        async for row in repo.stream_complaints(
            agency_code    = current_user.agency_code,
            borough        = borough,
            complaint_type = complaint_type,
            status         = status,
            start_date     = start_date,
            end_date       = end_date,
        ):
            # build CSV row — handle None and commas in strings
            values = [
                str(row.unique_key),
                str(row.created_date or ""),
                str(row.closed_date or ""),
                str(row.agency or ""),
                str(row.agency_name or ""),
                f'"{row.complaint_type or ""}"',   # quote strings that may have commas
                f'"{row.descriptor or ""}"',
                f'"{row.location_type or ""}"',
                str(row.incident_zip or ""),
                f'"{row.city or ""}"',
                str(row.borough or ""),
                str(row.status or ""),
                f'"{row.resolution_description or ""}"',
                str(row.latitude or ""),
                str(row.longitude or ""),
                str(row.resolution_action_updated_date or ""),
            ]
            yield ",".join(values) + "\n"

    # filename with today's date
    filename = f"complaints_{current_user.agency_code}_{date.today()}.csv"

    return StreamingResponse(
        content      = csv_generator(),
        media_type   = "text/csv",
        headers      = {
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )

    
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

# POST /complaints — invalidate cache

@router.post("/", response_model=ComplaintDetail, status_code=status.HTTP_201_CREATED)
async def create_complaint(
    request      : ComplaintCreate,
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    complaint = await repo.create(
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

    # invalidate all complaint list cache for this agency
    await cache_delete_pattern(f"complaints:{current_user.agency_code}:*")

    return complaint


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


  


