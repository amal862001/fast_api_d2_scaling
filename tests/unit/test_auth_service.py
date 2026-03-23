"""
Unit tests for services/auth_service.py

Covers:
  - hash_password / verify_password
  - create_access_token  (payload fields, role scopes)
  - decode_access_token  (valid, invalid, expired)
  - ROLE_SCOPES coverage for all roles
"""
import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from services.auth_service import (
    hash_password, verify_password,
    create_access_token, decode_access_token,
    ROLE_SCOPES
)
from config import settings
from models.user import PlatformUser


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def staff_user():
    return PlatformUser(
        id=1, email="james@nypd.nyc.gov",
        full_name="James NYPD", hashed_password="hashed",
        agency_code="NYPD", role="staff",
        created_at=datetime.now().replace(tzinfo=None)
    )


@pytest.fixture
def analyst_user():
    return PlatformUser(
        id=2, email="kevin@dpr.nyc.gov",
        full_name="Kevin DPR", hashed_password="hashed",
        agency_code="DPR", role="analyst",
        created_at=datetime.now().replace(tzinfo=None)
    )


@pytest.fixture
def admin_user():
    return PlatformUser(
        id=3, email="admin@doitt.nyc.gov",
        full_name="Admin DOITT", hashed_password="hashed",
        agency_code="DOITT", role="admin",
        created_at=datetime.now().replace(tzinfo=None)
    )


# ── Password hashing ──────────────────────────────────────────

def test_correct_password_verifies():
    """Correct plain text must verify against its hash."""
    hashed = hash_password("Password123!")
    assert verify_password("Password123!", hashed) is True


def test_wrong_password_fails():
    """Wrong plain text must never pass verification."""
    hashed = hash_password("Password123!")
    assert verify_password("WrongPassword!", hashed) is False


def test_different_passwords_produce_different_hashes():
    """Two different passwords must never produce the same hash."""
    h1 = hash_password("Password123!")
    h2 = hash_password("DifferentPass!")
    assert h1 != h2


# ── Token creation ────────────────────────────────────────────

def test_token_contains_all_required_fields(staff_user):
    """JWT must carry sub, agency_code, role, scopes, and exp."""
    token   = create_access_token(staff_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    for field in ("sub", "agency_code", "role", "scopes", "exp"):
        assert field in payload, f"Missing field: {field}"


def test_token_sub_matches_user_id(staff_user):
    """sub claim must equal the user's integer id as a string."""
    token   = create_access_token(staff_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"]         == str(staff_user.id)
    assert payload["agency_code"] == "NYPD"
    assert payload["role"]        == "staff"


def test_staff_token_has_read_only_scope(staff_user):
    """Staff role must only receive complaints:read — no write or admin."""
    token   = create_access_token(staff_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["scopes"] == ["complaints:read"]
    assert "admin"             not in payload["scopes"]
    assert "complaints:write"  not in payload["scopes"]
    assert "complaints:export" not in payload["scopes"]


def test_analyst_token_has_export_scope(analyst_user):
    """Analyst must get complaints:read and complaints:export."""
    token   = create_access_token(analyst_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert "complaints:read"   in payload["scopes"]
    assert "complaints:export" in payload["scopes"]
    assert "admin"             not in payload["scopes"]


def test_admin_token_has_all_scopes(admin_user):
    """Admin must carry all four scopes."""
    token   = create_access_token(admin_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert "complaints:read"   in payload["scopes"]
    assert "complaints:export" in payload["scopes"]
    assert "complaints:write"  in payload["scopes"]
    assert "admin"             in payload["scopes"]


# ── Token decoding ────────────────────────────────────────────

def test_decode_valid_token_returns_payload(staff_user):
    """decode_access_token must return the full payload dict for a valid token."""
    token   = create_access_token(staff_user)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["agency_code"] == "NYPD"


def test_decode_invalid_token_returns_none():
    """A tampered or made-up token must return None — never raise."""
    assert decode_access_token("invalid.token.here") is None


def test_decode_garbage_string_returns_none():
    """Completely random input must also return None gracefully."""
    assert decode_access_token("notaJWT") is None


def test_expired_token_raises_on_raw_decode(staff_user):
    """Manually crafted expired token must raise JWTError when decoded directly."""
    payload = {
        "sub"        : str(staff_user.id),
        "agency_code": staff_user.agency_code,
        "role"       : staff_user.role,
        "scopes"     : ["complaints:read"],
        "exp"        : datetime.now(timezone.utc) - timedelta(minutes=5)
    }
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    with pytest.raises(JWTError):
        jwt.decode(expired_token, settings.SECRET_KEY, algorithms=["HS256"])


def test_expired_token_returns_none_via_decode_helper(staff_user):
    """decode_access_token must return None (not raise) for expired tokens."""
    payload = {
        "sub"        : str(staff_user.id),
        "agency_code": staff_user.agency_code,
        "role"       : staff_user.role,
        "scopes"     : ["complaints:read"],
        "exp"        : datetime.now(timezone.utc) - timedelta(minutes=5)
    }
    expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    assert decode_access_token(expired_token) is None


# ── Role scopes coverage ──────────────────────────────────────

def test_role_scopes_covers_all_roles():
    """Every platform role must have at least one scope defined."""
    for role in ("staff", "analyst", "admin"):
        assert role in ROLE_SCOPES, f"Missing role: {role}"
        assert len(ROLE_SCOPES[role]) > 0, f"Empty scopes for: {role}"


def test_role_scopes_are_additive():
    """Higher roles must be supersets — analyst >= staff, admin >= analyst."""
    staff_set   = set(ROLE_SCOPES["staff"])
    analyst_set = set(ROLE_SCOPES["analyst"])
    admin_set   = set(ROLE_SCOPES["admin"])
    assert staff_set.issubset(analyst_set)
    assert analyst_set.issubset(admin_set)
