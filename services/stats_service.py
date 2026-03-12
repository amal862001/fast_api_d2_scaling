import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models.complaint import Complaint
from services.cache_service import get_redis
import json


# Compute and store all live stats into Redis

async def refresh_live_stats():
    async with AsyncSessionLocal() as db:
        try:
            await _refresh_borough_open_counts(db)
            await _refresh_complaints_last_hour(db)
            await _refresh_top_complaint_type(db)
            print(f"Live stats refreshed at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"Stats refresh failed: {e}")


# Open complaint count per borough

async def _refresh_borough_open_counts(db: AsyncSession):
    result = await db.execute(
        select(
            Complaint.borough,
            func.count(Complaint.unique_key).label("open_count")
        )
        .where(Complaint.status == "Open")
        .group_by(Complaint.borough)
    )
    rows   = result.fetchall()
    redis  = await get_redis()

    for row in rows:
        key = f"borough_stats:{row.borough}:open_count"
        await redis.setex(key, 120, str(row.open_count))


# Complaints filed in last hour

async def _refresh_complaints_last_hour(db: AsyncSession):
    one_hour_ago = datetime.now().replace(tzinfo=None) - timedelta(hours=1)

    result = await db.execute(
        select(func.count(Complaint.unique_key))
        .where(Complaint.created_date >= one_hour_ago)
    )
    count = result.scalar()
    redis = await get_redis()
    await redis.setex("global:complaints_last_hour", 120, str(count))


# Top complaint type in last 24 hours

async def _refresh_top_complaint_type(db: AsyncSession):
    yesterday = datetime.now().replace(tzinfo=None) - timedelta(hours=24)

    result = await db.execute(
        select(
            Complaint.complaint_type,
            func.count(Complaint.unique_key).label("total")
        )
        .where(Complaint.created_date >= yesterday)
        .group_by(Complaint.complaint_type)
        .order_by(func.count(Complaint.unique_key).desc())
        .limit(1)
    )
    row   = result.fetchone()
    redis = await get_redis()
    top   = row.complaint_type if row else "N/A"
    await redis.setex("global:top_complaint_type", 120, top)


# Total open complaints across all agencies

async def _get_total_open(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Complaint.unique_key))
        .where(Complaint.status == "Open")
    )
    return result.scalar() or 0


# Background loop — runs forever every 60 seconds

async def stats_refresh_loop():
    while True:
        await refresh_live_stats()
        await asyncio.sleep(60)