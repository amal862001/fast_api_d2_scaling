"""
Tests for routers/analytics.py
GET /complaint-types
GET /boroughs/stats
"""
import pytest
from tests.conftest import auth_header


class TestAnalytics:

    def test_complaint_types_authenticated(self, client, staff_token):
        """
        Authenticated request must return 200 with a list of complaint types.
        """
        r = client.get("/complaint-types", headers=auth_header(staff_token))
        assert r.status_code == 200
        data = r.json()
        assert "complaint_types" in data
        assert "total" in data
        assert isinstance(data["complaint_types"], list)

    def test_complaint_types_unauthenticated(self, client):
        """
        No token must return 401.
        """
        r = client.get("/complaint-types")
        assert r.status_code == 401

    def test_borough_stats_authenticated(self, client, staff_token):
        """
        Authenticated request must return 200 with agency and stats.
        """
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert r.status_code == 200
        data = r.json()
        assert "agency" in data
        assert "stats"  in data

    def test_borough_stats_scoped_to_agency(self, client, staff_token):
        """
        Borough stats must be scoped to the authenticated user's agency.
        NYPD staff must only see NYPD stats.
        """
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert r.json()["agency"] == "NYPD"

    def test_cache_header_present(self, client, staff_token):
        """
        Both analytics endpoints must return X-Cache header (HIT or MISS).
        This confirms the cache-aside pattern is working.
        """
        r = client.get("/boroughs/stats", headers=auth_header(staff_token))
        assert "X-Cache" in r.headers
        assert r.headers["X-Cache"] in ["HIT", "MISS"]
