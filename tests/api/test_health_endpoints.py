def test_liveness_always_200(client):
    """
    /health/live must always return 200.
    Docker uses this to restart crashed containers.
    If this fails Docker will restart the container in a loop.
    """
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readiness_returns_checks(client):
    """
    /health/ready must return all three checks.
    """
    response = client.get("/health/ready")
    assert response.status_code == 200
    checks = response.json()["checks"]
    assert "postgres" in checks
    assert "redis"    in checks
    assert "worker"   in checks


def test_readiness_postgres_ok(client):
    """
    PostgreSQL check must pass when DB is running.
    """
    response = client.get("/health/ready")
    assert response.json()["checks"]["postgres"] == "ok"


def test_readiness_redis_ok(client):
    """
    Redis check must pass when Redis is running.
    """
    response = client.get("/health/ready")
    assert response.json()["checks"]["redis"] == "ok"