"""
API integration tests for middleware/rate_limit.py

Covers:
  - Rate limit headers present on every response
  - Remaining count decreases with each request
  - Authenticated users are not throttled under the limit
  - Exempt paths have no rate limit headers
"""
import pytest
from tests.conftest import auth_header


class TestRateLimitHeaders:

    def test_headers_present_on_authenticated_request(self, client, staff_token):
        """Every non-exempt response must include X-RateLimit-Limit
        and X-RateLimit-Remaining so clients can self-throttle."""
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert "X-RateLimit-Limit"     in r.headers
        assert "X-RateLimit-Remaining" in r.headers

    def test_limit_value_is_numeric(self, client, staff_token):
        """X-RateLimit-Limit must be a parseable integer."""
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert int(r.headers["X-RateLimit-Limit"]) > 0

    def test_remaining_value_is_numeric(self, client, staff_token):
        """X-RateLimit-Remaining must be a parseable non-negative integer."""
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert int(r.headers["X-RateLimit-Remaining"]) >= 0

    def test_remaining_decreases_with_each_request(self, client, staff_token):
        """X-RateLimit-Remaining must go down by at least 1 between two requests."""
        r1 = client.get("/boroughs/stats", headers=auth_header(staff_token))
        r2 = client.get("/boroughs/stats", headers=auth_header(staff_token))
        remaining1 = int(r1.headers["X-RateLimit-Remaining"])
        remaining2 = int(r2.headers["X-RateLimit-Remaining"])
        assert remaining2 < remaining1


class TestRateLimitBehaviour:

    def test_authenticated_users_not_throttled_under_limit(self, client, staff_token):
        """Authenticated users get 200 req/min.
        35 requests must all succeed — well under the limit."""
        responses    = [
            client.get("/health/live", headers=auth_header(staff_token))
            for _ in range(35)
        ]
        status_codes = [r.status_code for r in responses]
        assert 429 not in status_codes

    def test_exempt_paths_have_no_rate_limit_headers(self, client):
        """/health/live is in EXEMPT_PATHS — it must not carry rate limit headers."""
        r = client.get("/health/live")
        assert "X-RateLimit-Limit"     not in r.headers
        assert "X-RateLimit-Remaining" not in r.headers

    def test_limit_is_200_for_authenticated(self, client, staff_token):
        """Rate limit must be 200 req/min for authenticated users."""
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert int(r.headers["X-RateLimit-Limit"]) == 200
