import pytest
from tests.conftest import auth_header





def test_authenticated_higher_limit(client, staff_token):
    """
    Authenticated users get 200 req/min — much higher than unauthenticated.
    Send 35 requests — all must pass (well under 200 limit).
    """
    responses = [
        client.get("/health/live", headers=auth_header(staff_token))
        for _ in range(35)
    ]
    status_codes = [r.status_code for r in responses]
    assert 429 not in status_codes


def test_rate_limit_headers_present(client, staff_token):
    """
    Every response must include X-RateLimit-Limit and X-RateLimit-Remaining.
    These help clients know how many requests they have left.
    """
    response = client.get(
        "/boroughs/stats",
        headers=auth_header(staff_token)
    )
    assert "X-RateLimit-Limit"     in response.headers
    assert "X-RateLimit-Remaining" in response.headers


def test_rate_limit_remaining_decreases(client, staff_token):
    """
    X-RateLimit-Remaining must decrease with each request.
    """
    r1 = client.get("/boroughs/stats", headers=auth_header(staff_token))
    r2 = client.get("/boroughs/stats", headers=auth_header(staff_token))

    remaining1 = int(r1.headers["X-RateLimit-Remaining"])
    remaining2 = int(r2.headers["X-RateLimit-Remaining"])

    assert remaining2 < remaining1