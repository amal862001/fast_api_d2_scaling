import pytest
from tests.conftest import auth_header


def test_staff_cannot_generate_api_key(client, staff_token):
    """
    Staff role has no admin scope.
    Generating API keys must return 403.
    """
    response = client.post(
        "/auth/api-keys",
        json={"scopes": ["complaints:read"]},
        headers=auth_header(staff_token)
    )
    assert response.status_code == 403


def test_admin_can_generate_api_key(client, admin_token):
    """
    Admin has all scopes including admin.
    Key generation must return 201 with a plain_key.
    """
    response = client.post(
        "/auth/api-keys",
        json={"scopes": ["complaints:read"]},
        headers=auth_header(admin_token)
    )
    assert response.status_code == 201
    data = response.json()
    assert "plain_key"   in data
    assert "key_prefix"  in data
    assert "id"          in data
    # plain key must start with nyc311_
    assert data["plain_key"].startswith("nyc311_")


def test_plain_key_only_returned_once(client, admin_token):
    """
    After creation the plain key must never appear again in GET /auth/api-keys.
    Only the prefix is shown — the hash is never returned.
    """
    # create a key
    create_response = client.post(
        "/auth/api-keys",
        json={"scopes": ["complaints:read"]},
        headers=auth_header(admin_token)
    )
    plain_key = create_response.json()["plain_key"]

    # list keys — plain key must not appear
    list_response = client.get(
        "/auth/api-keys",
        headers=auth_header(admin_token)
    )
    listed_keys = list_response.json()
    for key in listed_keys:
        assert "plain_key" not in key
        assert "key_hash"  not in key


def test_invalid_api_key_rejected(client):
    """
    A made-up API key must return 401.
    """
    response = client.get(
        "/complaints/",
        headers={"X-API-Key": "nyc311_fakekeynotreal"}
    )
    assert response.status_code == 401

