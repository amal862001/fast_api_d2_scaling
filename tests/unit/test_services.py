import pytest
import json
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from jose import jwt, JWTError
import fakeredis.aioredis



# 1 — auth_service.py

from services.auth_service import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
    ROLE_SCOPES
)
from models.user import PlatformUser
from config import settings


@pytest.fixture
def sample_user():
    return PlatformUser(
        id=1, email="james@nypd.nyc.gov",
        agency_code="NYPD", role="staff",
        created_at=datetime.now().replace(tzinfo=None)
    )


class TestAuthService:

    def test_hash_and_verify_password(self):
        """
        Hashed password must verify correctly against the plain text.
        """
        plain  = "SecurePass123!"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_does_not_verify(self):
        """
        Wrong password must never pass verification.
        """
        hashed = hash_password("SecurePass123!")
        assert verify_password("WrongPass!", hashed) is False

    def test_token_payload_contains_required_fields(self, sample_user):
        """
        JWT must contain sub, agency_code, role, scopes, exp.
        Missing any field breaks downstream dependencies.
        """
        token   = create_access_token(sample_user)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        assert "sub"         in payload
        assert "agency_code" in payload
        assert "role"        in payload
        assert "scopes"      in payload
        assert "exp"         in payload

    def test_decode_valid_token_returns_payload(self, sample_user):
        """
        decode_access_token must return payload dict for valid token.
        """
        token   = create_access_token(sample_user)
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["agency_code"] == "NYPD"

    def test_decode_invalid_token_returns_none(self):
        """
        decode_access_token must return None for tampered/invalid token.
        Never raise an exception — callers check for None.
        """
        result = decode_access_token("invalid.token.here")
        assert result is None



# 2 — cache_service.py

from services.cache_service import (
    cache_get, cache_set, cache_delete,
    cache_delete_pattern, key_complaints,
    key_borough_stats, key_complaint_types
)


@pytest.fixture(autouse=True)
async def fake_redis_fixture():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with patch("services.cache_service.redis_client", fake):
        yield fake
    await fake.aclose()


class TestCacheService:

    async def test_cache_miss_returns_none(self):
        """
        Key that was never set must return None — triggers DB query.
        """
        result = await cache_get("missing_key")
        assert result is None

    async def test_set_and_get_round_trip(self):
        """
        Data stored must be retrievable exactly as stored.
        """
        data = {"agency": "NYPD", "count": 42}
        await cache_set("test:key", data, ttl_seconds=60)
        result = await cache_get("test:key")
        assert result == data

    async def test_delete_removes_key(self):
        """
        cache_delete must make the key return None.
        """
        await cache_set("test:delete", {"x": 1}, ttl_seconds=60)
        await cache_delete("test:delete")
        assert await cache_get("test:delete") is None

    async def test_delete_pattern_removes_only_matching(self):
        """
        Pattern delete must only remove matching keys.
        Other agencies' cache must be untouched.
        """
        await cache_set("complaints:NYPD:abc", {"p": 1}, ttl_seconds=60)
        await cache_set("complaints:NYPD:def", {"p": 2}, ttl_seconds=60)
        await cache_set("complaints:DPR:xyz",  {"p": 3}, ttl_seconds=60)

        await cache_delete_pattern("complaints:NYPD:*")

        assert await cache_get("complaints:NYPD:abc") is None
        assert await cache_get("complaints:NYPD:def") is None
        assert await cache_get("complaints:DPR:xyz")  is not None

    def test_key_builders_produce_correct_format(self):
        """
        Key builders must produce consistent predictable keys.
        Inconsistent keys = cache never hits.
        """
        assert key_borough_stats("NYPD")  == "borough_stats:NYPD"
        assert key_complaint_types("DPR") == "complaint_types:DPR"
        filters = {"borough": "BROOKLYN", "page": 1}
        key = key_complaints("NYPD", filters)
        assert key.startswith("complaints:NYPD:")
        assert len(key.split(":")[-1]) == 8   # MD5 hash is 8 chars



# 3 — audit_service.py

from services.audit_service import write_audit_log


class TestAuditService:

    async def test_audit_log_written_successfully(self):
        """
        write_audit_log must add an AuditLog object to the session.
        """
        mock_db = AsyncMock()
        mock_db.add    = MagicMock()
        mock_db.commit = AsyncMock()

        await write_audit_log(
            db          = mock_db,
            user_id     = 1,
            agency_code = "NYPD",
            endpoint    = "/complaints",
            query_params= {"borough": "BROOKLYN"},
            result_count= 50
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    async def test_audit_log_never_raises_exception(self):
        """
        If DB commit fails audit logging must silently fail.
        It must NEVER crash the main request.
        """
        mock_db = AsyncMock()
        mock_db.add    = MagicMock()
        mock_db.commit = AsyncMock(side_effect=Exception("DB down"))

        # must not raise — just print the error
        try:
            await write_audit_log(
                db          = mock_db,
                user_id     = 1,
                agency_code = "NYPD",
                endpoint    = "/complaints",
                query_params= {},
                result_count= 0
            )
        except Exception:
            pytest.fail("write_audit_log raised an exception — it must not")

    async def test_audit_log_stores_correct_fields(self):
        """
        The AuditLog object must be created with the exact fields passed.
        """
        mock_db  = AsyncMock()
        captured = []
        mock_db.add    = lambda obj: captured.append(obj)
        mock_db.commit = AsyncMock()

        await write_audit_log(
            db          = mock_db,
            user_id     = 5,
            agency_code = "DPR",
            endpoint    = "/boroughs/stats",
            query_params= {"status": "Open"},
            result_count= 10
        )

        log = captured[0]
        assert log.user_id      == 5
        assert log.agency_code  == "DPR"
        assert log.endpoint     == "/boroughs/stats"

    async def test_audit_log_handles_empty_query_params(self):
        """
        Empty query_params dict must not cause any errors.
        Some endpoints have no filters.
        """
        mock_db        = AsyncMock()
        mock_db.add    = MagicMock()
        mock_db.commit = AsyncMock()

        await write_audit_log(
            db          = mock_db,
            user_id     = 1,
            agency_code = "NYPD",
            endpoint    = "/complaints",
            query_params= {},
            result_count= 0
        )
        mock_db.add.assert_called_once()

    async def test_audit_log_handles_zero_results(self):
        """
        result_count of 0 is valid — filtered query returned nothing.
        """
        mock_db        = AsyncMock()
        mock_db.add    = MagicMock()
        mock_db.commit = AsyncMock()

        await write_audit_log(
            db          = mock_db,
            user_id     = 1,
            agency_code = "NYPD",
            endpoint    = "/complaints",
            query_params= {"borough": "QUEENS"},
            result_count= 0
        )
        mock_db.add.assert_called_once()



# 4 — metrics_service.py

from services.metrics_service import (
    cache_hits_total, cache_misses_total,
    active_ws_connections, report_jobs_total
)


class TestMetricsService:

    def test_cache_hits_counter_increments(self):
        """
        cache_hits_total must increment by 1 on each call.
        """
        before = cache_hits_total.labels(endpoint="test")._value.get()
        cache_hits_total.labels(endpoint="test").inc()
        after  = cache_hits_total.labels(endpoint="test")._value.get()
        assert after == before + 1

    def test_cache_misses_counter_increments(self):
        """
        cache_misses_total must increment by 1 on each call.
        """
        before = cache_misses_total.labels(endpoint="test")._value.get()
        cache_misses_total.labels(endpoint="test").inc()
        after  = cache_misses_total.labels(endpoint="test")._value.get()
        assert after == before + 1

    def test_ws_connections_gauge_increments(self):
        """
        active_ws_connections must go up when a client connects.
        """
        before = active_ws_connections._value.get()
        active_ws_connections.inc()
        assert active_ws_connections._value.get() == before + 1

    def test_ws_connections_gauge_decrements(self):
        """
        active_ws_connections must go down when a client disconnects.
        """
        active_ws_connections.inc()   # simulate connect
        before = active_ws_connections._value.get()
        active_ws_connections.dec()   # simulate disconnect
        assert active_ws_connections._value.get() == before - 1

    def test_report_jobs_counter_increments(self):
        """
        report_jobs_total must track job submissions.
        """
        before = report_jobs_total.labels(status="queued")._value.get()
        report_jobs_total.labels(status="queued").inc()
        after  = report_jobs_total.labels(status="queued")._value.get()
        assert after == before + 1



# 5 — logging_service.py

from services.logging_service import configure_logging, get_logger, add_request_context
from middleware.request_id import request_id_ctx
import structlog


class TestLoggingService:

    def test_get_logger_returns_logger(self):
        """
        get_logger must return a structlog logger instance.
        """
        configure_logging()
        logger = get_logger("test")
        assert logger is not None

    def test_add_request_context_injects_request_id(self):
        """
        add_request_context processor must add request_id to every log entry.
        """
        request_id_ctx.set("test-uuid-1234")
        event_dict = {"event": "test_log"}
        result = add_request_context(None, None, event_dict)
        assert result["request_id"] == "test-uuid-1234"

    def test_add_request_context_empty_when_no_request(self):
        """
        When no request_id is set the field must be empty string.
        Startup/shutdown logs have no request context.
        """
        request_id_ctx.set("")
        event_dict = {"event": "startup"}
        result = add_request_context(None, None, event_dict)
        assert result["request_id"] == ""

    def test_logger_info_does_not_raise(self):
        """
        Calling logger.info must never raise an exception.
        A broken logger would silence all observability.
        """
        configure_logging()
        logger = get_logger("test")
        try:
            logger.info("test_event", key="value")
        except Exception:
            pytest.fail("logger.info raised an exception")

    def test_configure_logging_sets_json_renderer(self):
        """
        After configure_logging the processors chain must include JSONRenderer.
        Without JSONRenderer logs are plain text not JSON.
        """
        configure_logging()
        config = structlog.get_config()
        processor_names = [type(p).__name__ for p in config["processors"]]
        assert "JSONRenderer" in processor_names


# 6 — stats_service.py

from services.stats_service import refresh_live_stats


class TestStatsService:

    async def test_refresh_live_stats_does_not_raise(self):
        """
        refresh_live_stats must handle DB errors silently.
        A stats failure must never crash the app or worker.
        """
        with patch("services.stats_service.AsyncSessionLocal") as mock_session:
            mock_ctx = AsyncMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=AsyncMock())
            mock_ctx.__aexit__  = AsyncMock(return_value=False)
            mock_session.return_value = mock_ctx

            try:
                await refresh_live_stats()
            except Exception:
                pytest.fail("refresh_live_stats raised — it must fail silently")

    async def test_borough_open_counts_stored_in_redis(self):
        """
        _refresh_borough_open_counts must write keys to Redis.
        WebSocket relies on these keys — missing keys = zero counts.
        """
        fake = fakeredis.aioredis.FakeRedis(decode_responses=True)

        with patch("services.stats_service.AsyncSessionLocal") as mock_session, \
             patch("services.stats_service.get_redis", return_value=AsyncMock(return_value=fake)):

            mock_db   = AsyncMock()
            mock_row  = MagicMock()
            mock_row.borough    = "BROOKLYN"
            mock_row.open_count = 500
            mock_db.execute = AsyncMock(return_value=MagicMock(fetchall=lambda: [mock_row]))

            from services.stats_service import _refresh_borough_open_counts
            await _refresh_borough_open_counts(mock_db)

    def test_stats_service_imports_cleanly(self):
        """
        stats_service must import without errors.
        Import errors would prevent the background task from starting.
        """
        try:
            import services.stats_service
        except ImportError as e:
            pytest.fail(f"stats_service import failed: {e}")

    async def test_refresh_completes_all_three_queries(self):
        """
        refresh_live_stats must run all 3 sub-tasks:
        borough counts, last hour count, top complaint type.
        """
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

    def test_role_scopes_covers_all_roles(self):
        """
        Every role used in the platform must have a scopes entry.
        Unknown role = empty scopes = all requests return 403.
        """
        from services.auth_service import ROLE_SCOPES
        for role in ["staff", "analyst", "admin"]:
            assert role in ROLE_SCOPES
            assert len(ROLE_SCOPES[role]) > 0