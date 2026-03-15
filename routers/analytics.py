from fastapi import APIRouter, Depends, Response
from dependencies import get_current_user, get_complaint_repo
from models.user import PlatformUser
from repositories.complaint_repository import ComplaintRepository
from services.cache_service import (
    cache_get, cache_set,
    key_borough_stats, key_complaint_types
)

router = APIRouter(tags=["Analytics"])

# GET /complaint-types — TTL 3600s

@router.get("/complaint-types")
async def get_complaint_types(
    response     : Response,
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    key    = key_complaint_types(current_user.agency_code)
    cached = await cache_get(key, endpoint="complaint_types")

    if cached:
        response.headers["X-Cache"] = "HIT"
        return cached

    # cache miss — query DB
    types  = await repo.get_complaint_types(current_user.agency_code)
    result = {"complaint_types": types, "total": len(types)}

    await cache_set(key, result, ttl_seconds=3600)
    response.headers["X-Cache"] = "MISS"
    return result


# GET /boroughs/stats — TTL 300s 

@router.get("/boroughs/stats")
async def get_borough_stats(
    response     : Response,
    repo         : ComplaintRepository = Depends(get_complaint_repo),
    current_user : PlatformUser        = Depends(get_current_user)
):
    key    = key_borough_stats(current_user.agency_code)
    cached = await cache_get(key, endpoint="borough_stats")

    if cached:
        response.headers["X-Cache"] = "HIT"
        return cached

    # cache miss — run the GROUP BY query
    stats  = await repo.get_borough_stats(current_user.agency_code)
    result = {"agency": current_user.agency_code, "stats": stats}

    await cache_set(key, result, ttl_seconds=300)
    response.headers["X-Cache"] = "MISS"
    return result