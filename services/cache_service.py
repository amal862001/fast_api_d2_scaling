import json
import hashlib
from typing import Optional
import redis.asyncio as aioredis
from config import settings


# Redis client singleton

redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding       = "utf-8",
            decode_responses = True
        )
    return redis_client


# Generic cache helpers

async def cache_get(key: str) -> Optional[dict]:
    try:
        redis = await get_redis()
        value = await redis.get(key)
        if value is None:
            return None
        return json.loads(value)
    except Exception as e:
        print(f"Cache GET failed: {e}")
        return None     # never let cache failure break the request


async def cache_set(key: str, value: dict, ttl_seconds: int) -> None:
    try:
        redis = await get_redis()
        await redis.setex(key, ttl_seconds, json.dumps(value))
    except Exception as e:
        print(f"Cache SET failed: {e}")


async def cache_delete(key: str) -> None:
    try:
        redis = await get_redis()
        await redis.delete(key)
    except Exception as e:
        print(f"Cache DELETE failed: {e}")


async def cache_delete_pattern(pattern: str) -> None:
    try:
        redis  = await get_redis()
        keys   = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
    except Exception as e:
        print(f"Cache DELETE pattern failed: {e}")


# Cache key builders
def key_borough_stats(agency_code: str) -> str:
    return f"borough_stats:{agency_code}"


def key_complaint_types(agency_code: str) -> str:
    return f"complaint_types:{agency_code}"


def key_complaints(agency_code: str, filters: dict) -> str:
    # hash all filter params into a short key
    filters_str  = json.dumps(filters, sort_keys=True)
    filters_hash = hashlib.md5(filters_str.encode()).hexdigest()[:8]
    return f"complaints:{agency_code}:{filters_hash}"