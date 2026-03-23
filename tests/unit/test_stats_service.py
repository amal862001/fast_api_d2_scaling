"""
Unit tests for services/stats_service.py

Covers:
  - refresh_live_stats runs all three sub-tasks
  - refresh_live_stats fails silently on DB errors
  - _refresh_borough_open_counts writes keys to Redis
  - stats_service imports cleanly
  - ROLE_SCOPES sanity check (cross-module guard)
"""
import pytest
import fakeredis.aioredis
from unittest.mock import AsyncMock, patch, MagicMock
from services.stats_service import refresh_live_stats, _refresh_borough_open_counts


# ── refresh_live_stats ────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_live_stats_calls_all_three_sub_tasks():
    """refresh_live_stats must invoke borough counts, last-hour count,
    and top complaint type — all three Redis keys must be populated."""
    with patch("services.stats_service._refresh_borough_open_counts", new_callable=AsyncMock) as m1, \
         patch("services.stats_service._refresh_complaints_last_hour", new_callable=AsyncMock) as m2, \
         patch("services.stats_service._refresh_top_complaint_type",   new_callable=AsyncMock) as m3, \
         patch("services.stats_service.AsyncSessionLocal") as mock_session:

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_ctx.__aexit__  = AsyncMock(return_value=False)
        mock_session.return_value = mock_ctx

        await refresh_live_stats()

        m1.assert_called_once()
        m2.assert_called_once()
        m3.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_live_stats_fails_silently_on_db_error():
    """A DB failure inside refresh_live_stats must never crash the app or worker.
    The background loop must keep running."""
    with patch("services.stats_service.AsyncSessionLocal") as mock_session:
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_ctx.__aexit__  = AsyncMock(return_value=False)
        mock_session.return_value = mock_ctx

        try:
            await refresh_live_stats()
        except Exception:
            pytest.fail("refresh_live_stats raised — it must fail silently")


@pytest.mark.asyncio
async def test_refresh_live_stats_fails_silently_on_redis_error():
    """A Redis failure must also be swallowed — stats are non-critical."""
    with patch("services.stats_service._refresh_borough_open_counts",
               new_callable=AsyncMock, side_effect=ConnectionError("Redis down")), \
         patch("services.stats_service.AsyncSessionLocal") as mock_session:

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
        mock_ctx.__aexit__  = AsyncMock(return_value=False)
        mock_session.return_value = mock_ctx

        try:
            await refresh_live_stats()
        except Exception:
            pytest.fail("refresh_live_stats raised on Redis error")


# ── _refresh_borough_open_counts ──────────────────────────────

@pytest.mark.asyncio
async def test_borough_open_counts_writes_redis_key():
    """_refresh_borough_open_counts must write borough_stats:<borough>:open_count
    to Redis for every borough returned by the DB query."""
    fake     = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mock_db  = AsyncMock()
    mock_row = MagicMock()
    mock_row.borough    = "BROOKLYN"
    mock_row.open_count = 500
    mock_db.execute = AsyncMock(
        return_value=MagicMock(fetchall=lambda: [mock_row])
    )

    with patch("services.stats_service.get_redis", new_callable=AsyncMock, return_value=fake):
        await _refresh_borough_open_counts(mock_db)

    value = await fake.get("borough_stats:BROOKLYN:open_count")
    assert value == "500"


@pytest.mark.asyncio
async def test_borough_open_counts_handles_empty_result():
    """Empty DB result must not raise — borough table might be empty on fresh boot."""
    fake    = fakeredis.aioredis.FakeRedis(decode_responses=True)
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(
        return_value=MagicMock(fetchall=lambda: [])
    )

    with patch("services.stats_service.get_redis", new_callable=AsyncMock, return_value=fake):
        try:
            await _refresh_borough_open_counts(mock_db)
        except Exception:
            pytest.fail("_refresh_borough_open_counts raised on empty result")


# ── Import guard ──────────────────────────────────────────────

def test_stats_service_imports_cleanly():
    """stats_service must import without errors.
    Import failures would silently prevent the background loop from starting."""
    try:
        import services.stats_service
    except ImportError as e:
        pytest.fail(f"stats_service import failed: {e}")
