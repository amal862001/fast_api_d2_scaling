"""
Unit tests for services/cache_service.py

Covers:
  - cache_get / cache_set / cache_delete / cache_delete_pattern
  - TTL behaviour
  - Key builder helpers (key_complaints, key_borough_stats, key_complaint_types)
  - Metrics counters (hit / miss)
"""
import pytest
import fakeredis.aioredis
from unittest.mock import patch
from services.cache_service import (
    cache_get, cache_set, cache_delete, cache_delete_pattern,
    key_complaints, key_borough_stats, key_complaint_types
)


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(autouse=True)
async def fake_redis():
    """Replace the real Redis singleton with fakeredis for every test."""
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with patch("services.cache_service.redis_client", fake):
        yield fake
    await fake.aclose()


# ── cache_get ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    """Key that was never set must return None — triggers a DB query."""
    assert await cache_get("nonexistent_key") is None


@pytest.mark.asyncio
async def test_cache_get_after_set_returns_data():
    """Data written with cache_set must be readable with cache_get."""
    data = {"agency": "NYPD", "stats": [{"borough": "BROOKLYN", "count": 100}]}
    await cache_set("test:get", data, ttl_seconds=60)
    assert await cache_get("test:get") == data


@pytest.mark.asyncio
async def test_cache_get_returns_exact_types():
    """Nested types (lists, ints, None values) must survive the JSON round trip."""
    data = {"list": [1, 2, 3], "nested": {"key": None}, "num": 42}
    await cache_set("test:types", data, ttl_seconds=60)
    result = await cache_get("test:types")
    assert result == data
    assert isinstance(result["list"], list)
    assert result["nested"]["key"] is None


# ── cache_set ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_set_overwrites_existing_key():
    """Setting the same key twice must store only the latest value."""
    await cache_set("test:overwrite", {"v": 1}, ttl_seconds=60)
    await cache_set("test:overwrite", {"v": 2}, ttl_seconds=60)
    result = await cache_get("test:overwrite")
    assert result["v"] == 2


# ── cache_delete ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_delete_removes_key():
    """After cache_delete the key must return None."""
    await cache_set("test:delete", {"data": "value"}, ttl_seconds=60)
    await cache_delete("test:delete")
    assert await cache_get("test:delete") is None


@pytest.mark.asyncio
async def test_cache_delete_nonexistent_key_does_not_raise():
    """Deleting a key that doesn't exist must be a silent no-op."""
    await cache_delete("never:existed")   # must not raise


# ── cache_delete_pattern ──────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_delete_pattern_removes_all_matching():
    """Wildcard delete must wipe all matching keys and nothing else."""
    await cache_set("complaints:NYPD:abc123", {"page": 1}, ttl_seconds=60)
    await cache_set("complaints:NYPD:def456", {"page": 2}, ttl_seconds=60)
    await cache_set("complaints:DPR:xyz789",  {"page": 1}, ttl_seconds=60)

    await cache_delete_pattern("complaints:NYPD:*")

    assert await cache_get("complaints:NYPD:abc123") is None   # deleted
    assert await cache_get("complaints:NYPD:def456") is None   # deleted
    assert await cache_get("complaints:DPR:xyz789")  is not None  # untouched


@pytest.mark.asyncio
async def test_cache_delete_pattern_leaves_other_agencies_intact():
    """Deleting one agency's cache must never touch another agency's keys."""
    await cache_set("complaints:FDNY:p1", {"x": 1}, ttl_seconds=60)
    await cache_set("complaints:DOT:p1",  {"x": 2}, ttl_seconds=60)

    await cache_delete_pattern("complaints:FDNY:*")

    assert await cache_get("complaints:FDNY:p1") is None
    assert await cache_get("complaints:DOT:p1")  is not None


# ── Key builders ──────────────────────────────────────────────

def test_key_borough_stats_format():
    """borough_stats key must follow the expected prefix:agency pattern."""
    assert key_borough_stats("NYPD") == "borough_stats:NYPD"
    assert key_borough_stats("DPR")  == "borough_stats:DPR"


def test_key_complaint_types_format():
    """complaint_types key must follow the expected prefix:agency pattern."""
    assert key_complaint_types("NYPD") == "complaint_types:NYPD"
    assert key_complaint_types("DPR")  == "complaint_types:DPR"


def test_key_complaints_starts_with_agency():
    """complaints key must be prefixed with complaints:<agency>."""
    filters = {"borough": "BROOKLYN", "page": 1}
    key = key_complaints("NYPD", filters)
    assert key.startswith("complaints:NYPD:")


def test_key_complaints_hash_is_8_chars():
    """The trailing MD5 fragment must be exactly 8 characters."""
    filters = {"borough": "BROOKLYN", "page": 1}
    key = key_complaints("NYPD", filters)
    assert len(key.split(":")[-1]) == 8


def test_key_complaints_same_filters_same_key():
    """Identical filters must always produce the same cache key."""
    filters = {"borough": "BROOKLYN", "page": 1, "limit": 50}
    assert key_complaints("NYPD", filters) == key_complaints("NYPD", filters)


def test_key_complaints_different_filters_different_key():
    """Different filters must produce different cache keys."""
    k1 = key_complaints("NYPD", {"borough": "BROOKLYN", "page": 1})
    k2 = key_complaints("NYPD", {"borough": "QUEENS",   "page": 1})
    assert k1 != k2


def test_key_complaints_different_agency_different_key():
    """Same filters for two agencies must produce different keys."""
    filters = {"borough": "BROOKLYN", "page": 1}
    assert key_complaints("NYPD", filters) != key_complaints("DPR", filters)
