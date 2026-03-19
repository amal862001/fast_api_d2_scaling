import pytest
from pydantic import ValidationError
from schemas.complaint_schema import ComplaintCreate, BoroughEnum


# Tests

def test_valid_complaint_passes():
    """
    A complaint with all valid fields must pass validation.
    """
    complaint = ComplaintCreate(
        complaint_type = "Noise - Residential",
        borough        = "BROOKLYN",
        descriptor     = "Loud music",
        incident_zip   = "11201",
        city           = "New York"
    )
    assert complaint.borough == "BROOKLYN"


def test_borough_normalizes_lowercase():
    """
    Staff might type 'brooklyn' in lowercase.
    The validator must normalize it to 'BROOKLYN' automatically.
    """
    complaint = ComplaintCreate(
        complaint_type = "Noise - Residential",
        borough        = "brooklyn",
        descriptor     = "Loud music",
        incident_zip   = "11201",
        city           = "New York"
    )
    assert complaint.borough == "BROOKLYN"


def test_invalid_borough_rejected():
    """
    A borough that doesn't exist must be rejected with a validation error.
    Without this check bad data could slip into the database.
    """
    with pytest.raises(ValidationError):
        ComplaintCreate(
            complaint_type = "Noise - Residential",
            borough        = "LONDON",
            descriptor     = "Loud music",
            incident_zip   = "11201",
            city           = "New York"
        )


def test_invalid_zip_becomes_none():
    """
    Bad ZIP codes like 'N/A' or '00000' must be stored as None.
    This keeps the data clean — bad ZIP is better than fake ZIP.
    """
    complaint = ComplaintCreate(
        complaint_type = "Noise - Residential",
        borough        = "BROOKLYN",
        descriptor     = "Loud music",
        incident_zip   = "00000",
        city           = "New York"
    )
    assert complaint.incident_zip is None


def test_missing_required_field_rejected():
    """
    A complaint without complaint_type must fail validation.
    Required fields must always be present.
    """
    with pytest.raises(ValidationError):
        ComplaintCreate(
            borough    = "BROOKLYN",
            descriptor = "Loud music",
            city       = "New York"
        )


def test_all_five_boroughs_are_valid():
    """
    All five NYC boroughs must be accepted.
    If any borough is missing, staff from that borough
    cannot file complaints.
    """
    boroughs = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]
    for borough in boroughs:
        complaint = ComplaintCreate(
            complaint_type = "Noise - Residential",
            borough        = borough,
            descriptor     = "Test",
            incident_zip   = "10001",
            city           = "New York"
        )
        assert complaint.borough == borough