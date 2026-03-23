"""
API integration tests for routers/auth.py

Covers:
  POST /auth/login
  GET  /auth/me
"""
import pytest
from tests.conftest import auth_header


class TestLogin:

    def test_valid_credentials_return_token(self, client):
        """Valid login must return 200 with an access token and bearer type."""
        r = client.post("/auth/login", data={
            "username": "james@nypd.nyc.gov",
            "password": "Password"
        })
        assert r.status_code == 200
        assert "access_token" in r.json()
        assert r.json()["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, client):
        """Wrong password must return 401 — never 200 or 403."""
        r = client.post("/auth/login", data={
            "username": "james@nypd.nyc.gov",
            "password": "WrongPassword!"
        })
        assert r.status_code == 401

    def test_nonexistent_user_returns_401(self, client):
        """Unknown email must return 401 — must never reveal whether email exists."""
        r = client.post("/auth/login", data={
            "username": "nobody@fake.com",
            "password": "Password123!"
        })
        assert r.status_code == 401

    def test_missing_password_returns_422(self, client):
        """OAuth2 form with no password field must fail validation."""
        r = client.post("/auth/login", data={"username": "james@nypd.nyc.gov"})
        assert r.status_code == 422

    def test_empty_credentials_return_422(self, client):
        """Empty form body must return 422 — not 500."""
        r = client.post("/auth/login", data={})
        assert r.status_code == 422


class TestGetMe:

    def test_valid_token_returns_user_info(self, client, staff_token):
        """/auth/me with a valid token must return the authenticated user's profile."""
        r = client.get("/auth/me", headers=auth_header(staff_token))
        assert r.status_code == 200
        assert r.json()["email"]       == "james@nypd.nyc.gov"
        assert r.json()["agency_code"] == "NYPD"
        assert r.json()["role"]        == "staff"

    def test_no_token_returns_401(self, client):
        """/auth/me without any token must return 401."""
        r = client.get("/auth/me")
        assert r.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """A made-up token string must be rejected with 401."""
        r = client.get("/auth/me", headers={"Authorization": "Bearer fake.token.here"})
        assert r.status_code == 401

    def test_malformed_auth_header_returns_401(self, client):
        """Authorization header without 'Bearer' prefix must return 401."""
        r = client.get("/auth/me", headers={"Authorization": "Token somethingwrong"})
        assert r.status_code == 401

    def test_response_does_not_expose_password(self, client, staff_token):
        """/auth/me must never return hashed_password in the response body."""
        r = client.get("/auth/me", headers=auth_header(staff_token))
        assert "hashed_password" not in r.json()
        assert "password"        not in r.json()
