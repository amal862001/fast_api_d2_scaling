"""
Tests for routers/attachments.py
POST /complaints/{id}/attachments
GET  /complaints/{id}/attachments
GET  /attachments/{id}/download
"""
import pytest
from tests.conftest import auth_header


class TestAttachments:

    def test_upload_unsupported_file_type_rejected(self, client, staff_token):
        """
        Only JPEG, PNG, PDF allowed.
        Uploading a .txt file must return 400.
        """
        complaints = client.get(
            "/complaints/", headers=auth_header(staff_token)
        ).json()
        if not complaints:
            pytest.skip("No complaints available for test")
        unique_key = complaints[0]["unique_key"]

        r = client.post(
            f"/complaints/{unique_key}/attachments",
            files={"file": ("test.txt", b"hello", "text/plain")},
            headers=auth_header(staff_token)
        )
        assert r.status_code == 400

    def test_list_attachments_authenticated(self, client, staff_token):
        """
        Authenticated request must return 200 with attachments list.
        """
        complaints = client.get(
            "/complaints/", headers=auth_header(staff_token)
        ).json()
        if not complaints:
            pytest.skip("No complaints available")
        unique_key = complaints[0]["unique_key"]

        r = client.get(
            f"/complaints/{unique_key}/attachments",
            headers=auth_header(staff_token)
        )
        assert r.status_code == 200
        assert "attachments" in r.json()

    def test_list_attachments_unauthenticated(self, client, staff_token):
        """
        No token must return 401.
        """
        complaints = client.get(
            "/complaints/", headers=auth_header(staff_token)
        ).json()
        if not complaints:
            pytest.skip("No complaints available")
        unique_key = complaints[0]["unique_key"]

        r = client.get(f"/complaints/{unique_key}/attachments")
        assert r.status_code == 401

    def test_download_nonexistent_attachment(self, client, staff_token):
        """
        Downloading an attachment that doesn't exist must return 404.
        """
        r = client.get(
            "/attachments/999999/download",
            headers=auth_header(staff_token)
        )
        assert r.status_code == 404

    def test_list_attachments_wrong_agency(self, client, staff_token, analyst_token):
        """
        NYPD staff must not see DPR complaint attachments.
        Agency isolation must apply to attachments too.
        """
        dpr_complaints = client.get(
            "/complaints/", headers=auth_header(analyst_token)
        ).json()
        if not dpr_complaints:
            pytest.skip("No DPR complaints available")

        unique_key = dpr_complaints[0]["unique_key"]

        r = client.get(
            f"/complaints/{unique_key}/attachments",
            headers=auth_header(staff_token)
        )
        assert r.status_code in [404, 200]
        if r.status_code == 200:
            assert r.json()["total"] == 0
