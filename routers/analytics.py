from fastapi import APIRouter, Depends
from dependencies import get_current_user, get_complaint_repo
from models.user import PlatformUser
from repositories.complaint_repository import ComplaintRepository

router = APIRouter(tags=["Analytics"])


# Get distinct complaint types

@router.get("/complaint-types")
async def get_complaint_types(
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    types = await repo.get_complaint_types(current_user.agency_code)
    return {"complaint_types": types, "total": len(types)}


# Get borough stats

@router.get("/boroughs/stats")
async def get_borough_stats(
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    stats = await repo.get_borough_stats(current_user.agency_code)
    return {
        "agency" : current_user.agency_code,
        "stats"  : stats
    }