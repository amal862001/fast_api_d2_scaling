import pytest
import fakeredis.aioredis
from unittest.mock import patch


# Override the real Redis with fake Redis for all tests
@pytest.fixture(autouse=True)
async def fake_redis():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with patch("services.cache_service.redis_client", fake):
        yield fake
    await fake.aclose()


# Import after patch is set up 
from services.cache_service import cache_get, cache_set, cache_delete, cache_delete_pattern


# Tests

async def test_cache_miss_returns_none():
    """
    A key that was never set must return None.
    This is the cache MISS path — triggers a DB query.
    """
    result = await cache_get("nonexistent_key")
    assert result is None


async def test_cache_set_then_get_returns_data():
    """
    Data stored with cache_set must be retrievable with cache_get.
    This proves the full cache round trip works.
    """
    data = {"agency": "NYPD", "stats": [{"borough": "BROOKLYN", "count": 100}]}
    await cache_set("test_key", data, ttl_seconds=60)
    result = await cache_get("test_key")
    assert result == data


async def test_cache_delete_removes_key():
    """
    After cache_delete the key must return None.
    This is used when POST /complaints invalidates the cache.
    """
    await cache_set("test_key", {"data": "value"}, ttl_seconds=60)
    await cache_delete("test_key")
    result = await cache_get("test_key")
    assert result is None


async def test_cache_delete_pattern_removes_all_matching():
    """
    cache_delete_pattern must remove all keys matching the wildcard.
    When a new complaint is created all complaint cache keys for
    that agency must be wiped — not just one specific key.
    """
    await cache_set("complaints:NYPD:abc123", {"page": 1}, ttl_seconds=60)
    await cache_set("complaints:NYPD:def456", {"page": 2}, ttl_seconds=60)
    await cache_set("complaints:DPR:xyz789", {"page": 1},  ttl_seconds=60)

    await cache_delete_pattern("complaints:NYPD:*")

    assert await cache_get("complaints:NYPD:abc123") is None   # deleted 
    assert await cache_get("complaints:NYPD:def456") is None   # deleted 
    assert await cache_get("complaints:DPR:xyz789")  is not None  # not deleted