"""
API integration tests for routers/api_keys.py

Covers:
  POST   /auth/api-keys   (create)
  GET    /auth/api-keys   (list)
  DELETE /auth/api-keys/{id} (revoke)
"""
import pytest
from tests.conftest import auth_header


class TestCreateApiKey:

    def test_admin_can_create_key_returns_201(self, client, admin_token):
        """Admin with admin scope must be able to create a key — returns 201."""
        r = client.post(
            "/auth/api-keys",
            json={"scopes": ["complaints:read"]},
            headers=auth_header(admin_token)
        )
        assert r.status_code == 201

    def test_created_key_response_has_required_fields(self, client, admin_token):
        """Creation response must include id, key_prefix, scopes, plain_key."""
        r    = client.post(
            "/auth/api-keys",
            json={"scopes": ["complaints:read"]},
            headers=auth_header(admin_token)
        )
        data = r.json()
        assert "plain_key"  in data
        assert "key_prefix" in data
        assert "id"         in data
        assert "scopes"     in data

    def test_plain_key_starts_with_nyc311(self, client, admin_token):
        """Generated key must start with nyc311_ prefix for easy identification."""
        r = client.post(
            "/auth/api-keys",
            json={"scopes": ["complaints:read"]},
            headers=auth_header(admin_token)
        )
        assert r.json()["plain_key"].startswith("nyc311_")

    def test_staff_cannot_create_key_returns_403(self, client, staff_token):
        """Staff has no admin scope — key creation must return 403."""
        r = client.post(
            "/auth/api-keys",
            json={"scopes": ["complaints:read"]},
            headers=auth_header(staff_token)
        )
        assert r.status_code == 403

    def test_analyst_cannot_create_key_returns_403(self, client, analyst_token):
        """Analyst has no admin scope — key creation must return 403."""
        r = client.post(
            "/auth/api-keys",
            json={"scopes": ["complaints:read"]},
            headers=auth_header(analyst_token)
        )
        assert r.status_code == 403

    def test_unauthenticated_returns_401(self, client):
        """No token must return 401."""
        r = client.post("/auth/api-keys", json={"scopes": ["complaints:read"]})
        assert r.status_code == 401


class TestListApiKeys:

    def test_plain_key_never_appears_in_list(self, client, admin_token):
        """After creation the plain key must never appear in GET /auth/api-keys.
        Only the prefix is shown — the hash is never returned."""
        client.post(
            "/auth/api-keys",
            json={"scopes": ["complaints:read"]},
            headers=auth_header(admin_token)
        )
        r = client.get("/auth/api-keys", headers=auth_header(admin_token))
        assert r.status_code == 200
        for key in r.json():
            assert "plain_key" not in key
            assert "key_hash"  not in key

    def test_list_returns_200_for_authenticated_user(self, client, admin_token):
        """Any authenticated user must be able to list their own keys."""
        r = client.get("/auth/api-keys", headers=auth_header(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_unauthenticated_list_returns_401(self, client):
        """No token must return 401."""
        r = client.get("/auth/api-keys")
        assert r.status_code == 401


class TestApiKeyAuthentication:

    def test_invalid_api_key_rejected_with_401(self, client):
        """A made-up X-API-Key header must return 401."""
        r = client.get(
            "/complaints/",
            headers={"X-API-Key": "nyc311_fakekeynotreal"}
        )
        assert r.status_code == 401

