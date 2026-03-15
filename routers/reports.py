import json
import uuid
import asyncio
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from arq.connections import create_pool, RedisSettings
from dependencies import get_current_user, require_scope
from models.user import PlatformUser
from services.cache_service import get_redis
from config import settings
from services.metrics_service import report_jobs_total



router = APIRouter(prefix="/reports", tags=["Reports"])


async def get_arq_pool():
    return await create_pool(RedisSettings.from_dsn(settings.ARQ_REDIS_URL))


# ── POST /reports — enqueue job ───────────────────────────────

@router.post("")
async def submit_report(
    current_user: PlatformUser = Depends(require_scope("complaints:read"))
):
    job_id   = str(uuid.uuid4())
    arq_pool = await get_arq_pool()

    await arq_pool.enqueue_job(
        "generate_agency_report",
        job_id      = job_id,
        agency_code = current_user.agency_code,
        _job_id     = job_id
    )

    # write initial queued state to Redis
    redis = await get_redis()
    await redis.set(f"job:{job_id}:progress", json.dumps({
        "status"      : "queued",
        "progress_pct": 0,
        "started_at"  : None,
        "completed_at": None,
    }), ex=3600)

    report_jobs_total.labels(status="queued").inc()

    return {
        "job_id"      : job_id,
        "status"      : "queued",
        "submitted_at": datetime.now().replace(tzinfo=None).isoformat(),
        "stream_url"  : f"/reports/{job_id}/stream",
        "result_url"  : f"/reports/{job_id}/result",
    }


# ── GET /reports/{id} — poll job state ───────────────────────

@router.get("/{job_id}")
async def get_report_status(
    job_id      : str,
    current_user: PlatformUser = Depends(get_current_user)
):
    redis = await get_redis()
    raw   = await redis.get(f"job:{job_id}:progress")
    if not raw:
        raise HTTPException(status_code=404, detail="Job not found")
    return json.loads(raw)


# ── GET /reports/{id}/stream — SSE live progress ─────────────

@router.get("/{job_id}/stream")
async def stream_report(
    job_id      : str,
    current_user: PlatformUser = Depends(get_current_user)
):
    redis = await get_redis()

    async def event_generator():
        while True:
            raw = await redis.get(f"job:{job_id}:progress")

            if not raw:
                yield {
                    "event": "error",
                    "data" : json.dumps({"error": "job not found"})
                }
                break

            state = json.loads(raw)
            # push progress event
            yield {
                "event": "progress",
                "data" : json.dumps(state)
            }

            if state["status"] == "complete":
                # push final event with download URL
                yield {
                    "event": "complete",
                    "data" : json.dumps({
                        "type"        : "complete",
                        "job_id"      : job_id,
                        "download_url": f"/reports/{job_id}/result"
                    })
                }
                break

            if state["status"] == "failed":
                yield {
                    "event": "error",
                    "data" : json.dumps({"type": "failed", "job_id": job_id})
                }
                break

            await asyncio.sleep(0.5)   # poll every 500ms

    return EventSourceResponse(event_generator())


# ── GET /reports/{id}/result — final JSON ────────────────────

@router.get("/{job_id}/result")
async def get_report_result(
    job_id      : str,
    current_user: PlatformUser = Depends(require_scope("complaints:export"))
):
    redis = await get_redis()
    raw   = await redis.get(f"job:{job_id}:result")

    if not raw:
        progress = await redis.get(f"job:{job_id}:progress")
        if progress:
            state = json.loads(progress)
            raise HTTPException(
                status_code = 202,
                detail      = f"Not ready — status: {state['status']}, progress: {state['progress_pct']}%"
            )
        raise HTTPException(status_code=404, detail="Job not found")

    return json.loads(raw)