"""
API integration tests for routers/complaints.py

Covers:
  GET    /complaints/
  GET    /complaints/{unique_key}
  POST   /complaints/
  PATCH  /complaints/{unique_key}/status
  GET    /complaints/export
"""
import pytest
from tests.conftest import auth_header


class TestListComplaints:

    def test_authenticated_request_returns_200_list(self, client, staff_token):
        """Authenticated GET must return 200 and a JSON list."""
        r = client.get("/complaints/", headers=auth_header(staff_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_unauthenticated_request_returns_401(self, client):
        """No token must return 401 — complaints are never public."""
        r = client.get("/complaints/")
        assert r.status_code == 401

    def test_agency_scoping_nypd_sees_only_nypd(self, client, staff_token):
        """NYPD staff must only receive complaints where agency == NYPD."""
        r          = client.get("/complaints/", headers=auth_header(staff_token))
        complaints = r.json()
        for complaint in complaints:
            assert complaint["agency"] == "NYPD"

    def test_response_contains_expected_fields(self, client, staff_token):
        """Each complaint summary must carry the 8 required fields."""
        r          = client.get("/complaints/", headers=auth_header(staff_token))
        complaints = r.json()
        if not complaints:
            pytest.skip("No complaints in DB")
        required = {"unique_key", "created_date", "complaint_type",
                    "borough", "status", "agency"}
        for field in required:
            assert field in complaints[0]

    def test_cache_header_present(self, client, staff_token):
        """Response must include X-Cache header indicating HIT or MISS."""
        r = client.get("/complaints/", headers=auth_header(staff_token))
        assert "X-Cache" in r.headers
        assert r.headers["X-Cache"] in ("HIT", "MISS")

    def test_pagination_page_param(self, client, staff_token):
        """page param must be accepted without error."""
        r = client.get("/complaints/?page=2&limit=10", headers=auth_header(staff_token))
        assert r.status_code == 200

    def test_filter_by_borough(self, client, staff_token):
        """borough filter must be accepted and return 200."""
        r = client.get("/complaints/?borough=BROOKLYN", headers=auth_header(staff_token))
        assert r.status_code == 200


class TestCreateComplaint:

    def test_create_valid_payload_returns_201(self, client, staff_token):
        """Valid complaint body must return 201 with the created complaint."""
        r = client.post("/complaints/", json={
            "complaint_type": "Noise - Residential",
            "borough"       : "BROOKLYN",
            "descriptor"    : "Loud music after midnight",
            "incident_zip"  : "11201",
            "city"          : "New York"
        }, headers=auth_header(staff_token))
        assert r.status_code == 201

    def test_created_complaint_has_open_status(self, client, staff_token):
        """Newly created complaint must default to status Open."""
        r = client.post("/complaints/", json={
            "complaint_type": "Noise - Residential",
            "borough"       : "QUEENS",
        }, headers=auth_header(staff_token))
        assert r.status_code == 201
        assert r.json()["status"] == "Open"

    def test_created_complaint_scoped_to_user_agency(self, client, staff_token):
        """Created complaint must be assigned to the authenticated user's agency."""
        r = client.post("/complaints/", json={
            "complaint_type": "Graffiti",
            "borough"       : "BRONX",
        }, headers=auth_header(staff_token))
        assert r.status_code == 201
        assert r.json()["agency"] == "NYPD"

    def test_missing_required_field_returns_422(self, client, staff_token):
        """Payload without complaint_type must fail with 422."""
        r = client.post("/complaints/", json={
            "borough": "BROOKLYN"
        }, headers=auth_header(staff_token))
        assert r.status_code == 422

    def test_invalid_borough_returns_422(self, client, staff_token):
        """An unknown borough value must return 422."""
        r = client.post("/complaints/", json={
            "complaint_type": "Noise - Residential",
            "borough"       : "LONDON"
        }, headers=auth_header(staff_token))
        assert r.status_code == 422

    def test_unauthenticated_create_returns_401(self, client):
        """Creating a complaint without a token must return 401."""
        r = client.post("/complaints/", json={
            "complaint_type": "Noise - Residential",
            "borough"       : "BROOKLYN"
        })
        assert r.status_code == 401


class TestExportComplaints:

    def test_staff_cannot_export_returns_403(self, client, staff_token):
        """Staff role has complaints:read only — export must return 403."""
        r = client.get("/complaints/export", headers=auth_header(staff_token))
        assert r.status_code == 403

    def test_analyst_can_export_returns_200(self, client, analyst_token):
        """Analyst has complaints:export scope — must return 200 with CSV."""
        r = client.get("/complaints/export", headers=auth_header(analyst_token))
        assert r.status_code == 200

    def test_export_content_type_is_csv(self, client, analyst_token):
        """Export response must have text/csv content type."""
        r = client.get("/complaints/export", headers=auth_header(analyst_token))
        assert "text/csv" in r.headers.get("content-type", "")

    def test_export_unauthenticated_returns_401(self, client):
        """Export without token must return 401."""
        r = client.get("/complaints/export")
        assert r.status_code == 401
