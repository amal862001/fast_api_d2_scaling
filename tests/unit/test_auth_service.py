import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from services.auth_service import create_access_token, verify_password, hash_password
from config import settings
from models.user import PlatformUser


# Fake user
@pytest.fixture
def staff_user():
    return PlatformUser(
        id=1, email="james@nypd.nyc.gov",
        agency_code="NYPD", role="staff",
        created_at=datetime.now().replace(tzinfo=None)
    )

@pytest.fixture
def admin_user():
    return PlatformUser(
        id=2, email="admin@doitt.nyc.gov",
        agency_code="DOITT", role="admin",
        created_at=datetime.now().replace(tzinfo=None)
    )


# Tests

def test_correct_password_verifies():
    hashed = hash_password("Password123!")
    assert verify_password("Password123!", hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("Password123!")
    assert verify_password("WrongPassword!", hashed) is False


def test_token_contains_correct_data(staff_user):
    token   = create_access_token(staff_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"]         == str(staff_user.id)
    assert payload["agency_code"] == "NYPD"
    assert payload["role"]        == "staff"


def test_staff_scope_is_read_only(staff_user):
    token   = create_access_token(staff_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert payload["scopes"] == ["complaints:read"]
    assert "admin" not in payload["scopes"]


def test_admin_has_all_scopes(admin_user):
    token   = create_access_token(admin_user)
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    assert "complaints:read"   in payload["scopes"]
    assert "complaints:export" in payload["scopes"]
    assert "complaints:write"  in payload["scopes"]
    assert "admin"             in payload["scopes"]


def test_expired_token_rejected(staff_user):
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