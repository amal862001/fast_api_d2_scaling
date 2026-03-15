import json
from datetime import datetime
from sqlalchemy import text
from database import AsyncSessionLocal

# This module defines the background worker function for generating agency reports.

async def _set_progress(redis, job_id: str, pct: int, status: str = "running", extra: dict = {}):
    payload = {
        "status"      : status,
        "progress_pct": pct,
        "started_at"  : extra.get("started_at"),
        "completed_at": extra.get("completed_at"),
    }
    await redis.set(f"job:{job_id}:progress", json.dumps(payload), ex=86400)


async def generate_agency_report(ctx: dict, job_id: str, agency_code: str):
    redis      = ctx["redis"]
    started_at = datetime.now().replace(tzinfo=None).isoformat()

    await _set_progress(redis, job_id, 0, "running", {"started_at": started_at})

    async with AsyncSessionLocal() as db:
        try:
            await _set_progress(redis, job_id, 10, "running", {"started_at": started_at})
            count_result = await db.execute(text(
                "SELECT COUNT(*) FROM nyc_311_service_requests WHERE agency = :agency"
            ), {"agency": agency_code})
            total_rows = count_result.scalar() or 0

            await _set_progress(redis, job_id, 40, "running", {"started_at": started_at})
            resolution_result = await db.execute(text("""
                SELECT
                    borough,
                    complaint_type,
                    COUNT(*)                                             AS total_complaints,
                    ROUND(AVG(EXTRACT(EPOCH FROM (
                        closed_date - created_date)) / 3600)::numeric, 2)
                                                                         AS avg_resolution_hours,
                    ROUND(MIN(EXTRACT(EPOCH FROM (
                        closed_date - created_date)) / 3600)::numeric, 2)
                                                                         AS min_resolution_hours,
                    ROUND(MAX(EXTRACT(EPOCH FROM (
                        closed_date - created_date)) / 3600)::numeric, 2)
                                                                         AS max_resolution_hours,
                    COUNT(*) FILTER (WHERE status = 'Open')             AS open_count,
                    COUNT(*) FILTER (WHERE status = 'Closed')           AS closed_count
                FROM nyc_311_service_requests
                WHERE agency       = :agency
                  AND closed_date  IS NOT NULL
                  AND closed_date  > created_date
                GROUP BY borough, complaint_type
                ORDER BY borough, avg_resolution_hours DESC
            """), {"agency": agency_code})
            resolution_rows = resolution_result.fetchall()

            await _set_progress(redis, job_id, 70, "running", {"started_at": started_at})
            monthly_result = await db.execute(text("""
                SELECT
                    TO_CHAR(created_date, 'YYYY-MM') AS month,
                    COUNT(*)                          AS total,
                    COUNT(*) FILTER (WHERE status = 'Closed') AS closed
                FROM nyc_311_service_requests
                WHERE agency = :agency
                GROUP BY TO_CHAR(created_date, 'YYYY-MM')
                ORDER BY month DESC
                LIMIT 24
            """), {"agency": agency_code})
            monthly_rows = monthly_result.fetchall()

            await _set_progress(redis, job_id, 90, "running", {"started_at": started_at})
            completed_at = datetime.now().replace(tzinfo=None).isoformat()

            result = {
                "job_id"      : job_id,
                "agency_code" : agency_code,
                "generated_at": completed_at,
                "total_rows"  : total_rows,
                "resolution_by_type": [
                    {
                        "borough"             : r.borough,
                        "complaint_type"      : r.complaint_type,
                        "total_complaints"    : r.total_complaints,
                        "avg_resolution_hours": float(r.avg_resolution_hours) if r.avg_resolution_hours else None,
                        "min_resolution_hours": float(r.min_resolution_hours) if r.min_resolution_hours else None,
                        "max_resolution_hours": float(r.max_resolution_hours) if r.max_resolution_hours else None,
                        "open_count"          : r.open_count,
                        "closed_count"        : r.closed_count,
                    }
                    for r in resolution_rows
                ],
                "monthly_trend": [
                    {"month": r.month, "total": r.total, "closed": r.closed}
                    for r in monthly_rows
                ]
            }

            await redis.set(f"job:{job_id}:result", json.dumps(result), ex=86400)
            await _set_progress(redis, job_id, 100, "complete", {
                "started_at"  : started_at,
                "completed_at": completed_at,
            })
            print(f"Report job {job_id} complete — {len(resolution_rows)} rows")

        except Exception as e:
            await _set_progress(redis, job_id, 0, "failed", {
                "started_at"  : started_at,
                "completed_at": datetime.now().replace(tzinfo=None).isoformat(),
            })
            print(f"Report job {job_id} FAILED: {e}")
            raise