import pytest
from models.user import PlatformUser
from datetime import datetime
import httpx


# Fake user factory
# creates a PlatformUser object without touching the database

@pytest.fixture
def staff_user():
    return PlatformUser(
        id           = 1,
        email        = "james@nypd.nyc.gov",
        full_name    = "James NYPD",
        hashed_password = "hashed",
        agency_code  = "NYPD",
        role         = "staff",
        created_at   = datetime.now().replace(tzinfo=None),
    )

@pytest.fixture
def analyst_user():
    return PlatformUser(
        id           = 2,
        email        = "kevin@dpr.nyc.gov",
        full_name    = "Kevin DPR",
        hashed_password = "hashed",
        agency_code  = "DPR",
        role         = "analyst",
        created_at   = datetime.now().replace(tzinfo=None),
    )

@pytest.fixture
def admin_user():
    return PlatformUser(
        id           = 3,
        email        = "admin@doitt.nyc.gov",
        full_name    = "Admin DOITT",
        hashed_password = "hashed",
        agency_code  = "DOITT",
        role         = "admin",
        created_at   = datetime.now().replace(tzinfo=None),
    )


BASE_URL = "http://localhost:8000"

# HTTP client shared across all API tests
@pytest.fixture
def client():
    return httpx.Client(base_url=BASE_URL)

# Login helper — returns token for any user
@pytest.fixture
def staff_token(client):
    response = client.post("/auth/login", data={
        "username": "james@nypd.nyc.gov",
        "password": "Password"
    })
    return response.json()["access_token"]

@pytest.fixture
def admin_token(client):
    response = client.post("/auth/login", data={
        "username": "admin@doitt.nyc.gov",
        "password": "Password"
    })
    return response.json()["access_token"]

@pytest.fixture
def analyst_token(client):
    response = client.post("/auth/login", data={
        "username": "kevin@dpr.nyc.gov",
        "password": "Password"
    })
    return response.json()["access_token"]

# Auth header helper
def auth_header(token):
    return {"Authorization": f"Bearer {token}"}
