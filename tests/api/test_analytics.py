"""
API integration tests for routers/analytics.py

Covers:
  GET /complaint-types
  GET /boroughs/stats
"""
import pytest
from tests.conftest import auth_header


class TestComplaintTypes:

    def test_authenticated_returns_200_with_list(self, client, staff_token):
        """Authenticated request must return 200 with complaint_types list and total."""
        r    = client.get("/complaint-types", headers=auth_header(staff_token))
        assert r.status_code == 200
        data = r.json()
        assert "complaint_types" in data
        assert "total"           in data
        assert isinstance(data["complaint_types"], list)

    def test_total_matches_list_length(self, client, staff_token):
        """total field must equal the length of the complaint_types list."""
        r    = client.get("/complaint-types", headers=auth_header(staff_token))
        data = r.json()
        assert data["total"] == len(data["complaint_types"])

    def test_unauthenticated_returns_401(self, client):
        """No token must return 401."""
        r = client.get("/complaint-types")
        assert r.status_code == 401

    def test_cache_header_present(self, client, staff_token):
        """Response must include X-Cache: HIT or MISS header."""
        r = client.get("/complaint-types", headers=auth_header(staff_token))
        assert "X-Cache" in r.headers
        assert r.headers["X-Cache"] in ("HIT", "MISS")

    def test_second_request_is_cache_hit(self, client, staff_token):
        """The second identical request must return X-Cache: HIT."""
        client.get("/complaint-types", headers=auth_header(staff_token))   # warm cache
        r2 = client.get("/complaint-types", headers=auth_header(staff_token))
        assert r2.headers.get("X-Cache") == "HIT"


class TestBoroughStats:

    def test_authenticated_returns_200_with_agency_and_stats(self, client, staff_token):
        """Authenticated request must return 200 with agency and stats keys."""
        r    = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert r.status_code == 200
        data = r.json()
        assert "agency" in data
        assert "stats"  in data

    def test_stats_scoped_to_authenticated_agency(self, client, staff_token):
        """Borough stats must reflect the authenticated user's agency — not all agencies."""
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert r.json()["agency"] == "NYPD"

    def test_stats_list_contains_expected_keys(self, client, staff_token):
        """Each stat entry must have borough, total, open, and closed counts."""
        r     = client.get("/boroughs/stats", headers=auth_header(staff_token))
        stats = r.json()["stats"]
        if not stats:
            pytest.skip("No stats available — DB may be empty")
        for entry in stats:
            assert "borough" in entry
            assert "total"   in entry
            assert "open"    in entry
            assert "closed"  in entry

    def test_unauthenticated_borough_stats_returns_401(self, client):
        """No token must return 401."""
        r = client.get("/boroughs/stats")
        assert r.status_code == 401

    def test_borough_stats_cache_header_present(self, client, staff_token):
        """Response must include X-Cache: HIT or MISS header."""
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert "X-Cache" in r.headers
        assert r.headers["X-Cache"] in ("HIT", "MISS")

    def test_analyst_sees_own_agency_stats(self, client, analyst_token):
        """DPR analyst must see DPR stats, not NYPD stats."""
        r = client.get("/boroughs/stats", headers=auth_header(analyst_token))
        assert r.status_code == 200
        assert r.json()["agency"] == "DPR"
