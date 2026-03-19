import pytest
from tests.conftest import auth_header


def test_login_valid_credentials(client):
    """
    Valid login must return 200 and an access token.
    This is the entry point for all platform users.
    """
    response = client.post("/auth/login", data={
        "username": "james@nypd.nyc.gov",
        "password": "Password"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"


def test_login_wrong_password(client):
    """
    Wrong password must return 401.
    If this fails anyone can log in without a password.
    """
    response = client.post("/auth/login", data={
        "username": "james@nypd.nyc.gov",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    """
    A user that doesn't exist must return 401.
    Must never reveal whether the email exists or not.
    """
    response = client.post("/auth/login", data={
        "username": "nobody@fake.com",
        "password": "Password123!"
    })
    assert response.status_code == 401


def test_get_me_with_valid_token(client, staff_token):
    """
    /auth/me with a valid token must return the user's info.
    """
    response = client.get("/auth/me", headers=auth_header(staff_token))
    assert response.status_code == 200
    assert response.json()["email"] == "james@nypd.nyc.gov"
    assert response.json()["agency_code"] == "NYPD"


def test_get_me_without_token(client):
    """
    /auth/me without a token must return 401.
    No token = no identity = no access.
    """
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_get_me_with_invalid_token(client):
    """
    A made-up token must be rejected with 401.
    """
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer fake.token.here"}
    )
    assert response.status_code == 401

    