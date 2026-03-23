"""
Unit tests for services/metrics_service.py

Covers:
  - cache_hits_total counter
  - cache_misses_total counter
  - active_ws_connections gauge (inc / dec)
  - report_jobs_total counter
"""
import pytest
from services.metrics_service import (
    cache_hits_total, cache_misses_total,
    active_ws_connections, report_jobs_total
)


# ── Cache counters ────────────────────────────────────────────

def test_cache_hits_counter_increments():
    """cache_hits_total must go up by exactly 1 on each .inc() call."""
    before = cache_hits_total.labels(endpoint="test_hits")._value.get()
    cache_hits_total.labels(endpoint="test_hits").inc()
    assert cache_hits_total.labels(endpoint="test_hits")._value.get() == before + 1


def test_cache_misses_counter_increments():
    """cache_misses_total must go up by exactly 1 on each .inc() call."""
    before = cache_misses_total.labels(endpoint="test_misses")._value.get()
    cache_misses_total.labels(endpoint="test_misses").inc()
    assert cache_misses_total.labels(endpoint="test_misses")._value.get() == before + 1


def test_cache_hits_and_misses_are_independent():
    """Incrementing hits must not affect misses and vice versa."""
    hits_before   = cache_hits_total.labels(endpoint="isolation")._value.get()
    misses_before = cache_misses_total.labels(endpoint="isolation")._value.get()

    cache_hits_total.labels(endpoint="isolation").inc()

    assert cache_hits_total.labels(endpoint="isolation")._value.get()   == hits_before + 1
    assert cache_misses_total.labels(endpoint="isolation")._value.get() == misses_before


# ── WebSocket gauge ───────────────────────────────────────────

def test_ws_connections_gauge_increments():
    """active_ws_connections must increase when a client connects."""
    before = active_ws_connections._value.get()
    active_ws_connections.inc()
    assert active_ws_connections._value.get() == before + 1


def test_ws_connections_gauge_decrements():
    """active_ws_connections must decrease when a client disconnects."""
    active_ws_connections.inc()        # simulate connect
    before = active_ws_connections._value.get()
    active_ws_connections.dec()        # simulate disconnect
    assert active_ws_connections._value.get() == before - 1


def test_ws_connections_connect_disconnect_net_zero():
    """One connect + one disconnect must leave the gauge unchanged."""
    before = active_ws_connections._value.get()
    active_ws_connections.inc()
    active_ws_connections.dec()
    assert active_ws_connections._value.get() == before


# ── Report jobs counter ───────────────────────────────────────

def test_report_jobs_queued_increments():
    """report_jobs_total[queued] must go up when a job is submitted."""
    before = report_jobs_total.labels(status="queued")._value.get()
    report_jobs_total.labels(status="queued").inc()
    assert report_jobs_total.labels(status="queued")._value.get() == before + 1


def test_report_jobs_labels_are_independent():
    """queued, complete, and failed labels must each track independently."""
    q_before = report_jobs_total.labels(status="queued")._value.get()
    c_before = report_jobs_total.labels(status="complete")._value.get()
    f_before = report_jobs_total.labels(status="failed")._value.get()

    report_jobs_total.labels(status="complete").inc()

    assert report_jobs_total.labels(status="queued")._value.get()   == q_before
    assert report_jobs_total.labels(status="complete")._value.get() == c_before + 1
    assert report_jobs_total.labels(status="failed")._value.get()   == f_before
