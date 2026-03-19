import pytest
from tests.conftest import auth_header


def test_get_complaints_authenticated(client, staff_token):
    """
    Authenticated request must return 200 and a list.
    """
    response = client.get("/complaints/", headers=auth_header(staff_token))
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_complaints_unauthenticated(client):
    """
    No token must return 401 — complaints are not public.
    """
    response = client.get("/complaints/")
    assert response.status_code == 401


def test_agency_scoping(client, staff_token):
    """
    NYPD staff must only see NYPD complaints.
    This is the core access control guarantee.
    """
    response = client.get("/complaints/", headers=auth_header(staff_token))
    complaints = response.json()
    for complaint in complaints:
        assert complaint["agency"] == "NYPD"


def test_create_complaint_valid(client, staff_token):
    """
    Valid complaint creation must return 201.
    """
    response = client.post("/complaints/", json={
        "complaint_type": "Noise - Residential",
        "borough"       : "BROOKLYN",
        "descriptor"    : "Loud music after midnight",
        "incident_zip"  : "11201",
        "city"          : "New York"
    }, headers=auth_header(staff_token))
    assert response.status_code == 201



def test_export_as_staff_forbidden(client, staff_token):
    """
    Staff scope is complaints:read only.
    Export requires complaints:export — must return 403.
    """
    response = client.get(
        "/complaints/export",
        headers=auth_header(staff_token)
    )
    assert response.status_code == 403


def test_export_as_analyst_allowed(client, analyst_token):
    """
    Analyst has complaints:export scope — must be allowed.
    """
    response = client.get(
        "/complaints/export",
        headers=auth_header(analyst_token)
    )
    assert response.status_code == 200