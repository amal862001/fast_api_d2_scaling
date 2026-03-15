from datetime import datetime
from fastapi import APIRouter
from sqlalchemy import text
from database import AsyncSessionLocal
from services.cache_service import get_redis

router = APIRouter(prefix="/health", tags=["Health"])


# ── GET /health/live — always 200, used by Docker to restart crashed containers

@router.get("/live")
async def liveness():
    return {
        "status"   : "ok",
        "timestamp": datetime.now().replace(tzinfo=None).isoformat()
    }


# ── GET /health/ready — checks all dependencies

@router.get("/ready")
async def readiness():
    checks  = {}
    healthy = True

    # ── PostgreSQL ────────────────────────────────────────────
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text(
                "SELECT 1 FROM nyc_311_service_requests LIMIT 1"
            ))
        checks["postgres"] = "ok"
    except Exception as e:
        checks["postgres"] = f"failed: {str(e)}"
        healthy = False

    # ── Redis ─────────────────────────────────────────────────
    try:
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"failed: {str(e)}"
        healthy = False

    # ── ARQ worker heartbeat ──────────────────────────────────
    try:
        redis       = await get_redis()
        worker_keys = await redis.keys("arq:*")
        checks["worker"] = "ok" if worker_keys else "degraded"
    except Exception as e:
        checks["worker"] = f"failed: {str(e)}"

    status_code = 200 if healthy else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code = status_code,
        content     = {
            "status": "ready" if healthy else "degraded",
            "checks": checks,
            "timestamp": datetime.now().replace(tzinfo=None).isoformat()
        }
    )