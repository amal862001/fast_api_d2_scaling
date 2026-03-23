"""
Unit tests for services/audit_service.py

Covers:
  - write_audit_log stores correct fields
  - write_audit_log never raises — even if DB commit fails
  - Edge cases: empty query_params, zero result_count
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from services.audit_service import write_audit_log


# ── Helpers ───────────────────────────────────────────────────

def make_mock_db():
    mock_db        = AsyncMock()
    mock_db.add    = MagicMock()
    mock_db.commit = AsyncMock()
    return mock_db


# ── Tests ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_calls_db_add_and_commit():
    """write_audit_log must add one AuditLog and commit exactly once."""
    db = make_mock_db()
    await write_audit_log(
        db=db, user_id=1, agency_code="NYPD",
        endpoint="/complaints", query_params={"borough": "BROOKLYN"},
        result_count=50
    )
    db.add.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_audit_log_stores_correct_fields():
    """The AuditLog object must carry exactly the values that were passed in."""
    db       = AsyncMock()
    captured = []
    db.add    = lambda obj: captured.append(obj)
    db.commit = AsyncMock()

    await write_audit_log(
        db=db, user_id=5, agency_code="DPR",
        endpoint="/boroughs/stats", query_params={"status": "Open"},
        result_count=10
    )

    log = captured[0]
    assert log.user_id      == 5
    assert log.agency_code  == "DPR"
    assert log.endpoint     == "/boroughs/stats"
    assert log.query_params == {"status": "Open"}
    assert log.result_count == 10


@pytest.mark.asyncio
async def test_audit_log_never_raises_on_db_failure():
    """If DB commit fails audit logging must swallow the error silently.
    It must NEVER crash the main request that called it."""
    db        = AsyncMock()
    db.add    = MagicMock()
    db.commit = AsyncMock(side_effect=Exception("DB connection lost"))

    try:
        await write_audit_log(
            db=db, user_id=1, agency_code="NYPD",
            endpoint="/complaints", query_params={}, result_count=0
        )
    except Exception:
        pytest.fail("write_audit_log raised — it must fail silently")


@pytest.mark.asyncio
async def test_audit_log_handles_empty_query_params():
    """Empty query_params dict is valid — endpoints like /health have no filters."""
    db = make_mock_db()
    await write_audit_log(
        db=db, user_id=1, agency_code="NYPD",
        endpoint="/health/ready", query_params={}, result_count=0
    )
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_audit_log_handles_zero_result_count():
    """result_count of 0 is valid — a filtered query that matched nothing."""
    db = make_mock_db()
    await write_audit_log(
        db=db, user_id=1, agency_code="NYPD",
        endpoint="/complaints", query_params={"borough": "QUEENS"},
        result_count=0
    )
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_audit_log_handles_none_query_params():
    """None query_params must not raise — some callers may pass None."""
    db = make_mock_db()
    try:
        await write_audit_log(
            db=db, user_id=1, agency_code="NYPD",
            endpoint="/complaints", query_params=None, result_count=5
        )
    except Exception:
        pytest.fail("write_audit_log raised on None query_params")
