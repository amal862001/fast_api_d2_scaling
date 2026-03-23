"""
API integration tests for routers/health.py

Covers:
  GET /health/live
  GET /health/ready
"""
import pytest


class TestLiveness:

    def test_always_returns_200(self, client):
        """/health/live must always return 200.
        Docker uses this to decide whether to restart the container."""
        r = client.get("/health/live")
        assert r.status_code == 200

    def test_status_field_is_ok(self, client):
        """Response body must contain status: ok."""
        r = client.get("/health/live")
        assert r.json()["status"] == "ok"

    def test_timestamp_field_present(self, client):
        """Response must include a timestamp for log correlation."""
        r = client.get("/health/live")
        assert "timestamp" in r.json()

    def test_no_auth_required(self, client):
        """/health/live must be accessible without any token."""
        r = client.get("/health/live")
        assert r.status_code != 401


class TestReadiness:

    def test_returns_200_when_healthy(self, client):
        """/health/ready must return 200 when all dependencies are up."""
        r = client.get("/health/ready")
        assert r.status_code == 200

    def test_response_has_checks_dict(self, client):
        """Response must contain a checks object with all service statuses."""
        r      = client.get("/health/ready")
        checks = r.json()["checks"]
        assert "postgres" in checks
        assert "redis"    in checks
        assert "worker"   in checks

    def test_postgres_check_passes(self, client):
        """postgres check must report ok when the DB container is running."""
        r = client.get("/health/ready")
        assert r.json()["checks"]["postgres"] == "ok"

    def test_redis_check_passes(self, client):
        """redis check must report ok when the Redis container is running."""
        r = client.get("/health/ready")
        assert r.json()["checks"]["redis"] == "ok"

    def test_status_field_is_ready(self, client):
        """Top-level status must be ready when all checks pass."""
        r = client.get("/health/ready")
        assert r.json()["status"] == "ready"

    def test_readiness_no_auth_required(self, client):
        """/health/ready must be accessible without any token."""
        r = client.get("/health/ready")
        assert r.status_code != 401
