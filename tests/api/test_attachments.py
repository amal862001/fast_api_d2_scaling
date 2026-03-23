"""
API integration tests for routers/attachments.py

Covers:
  POST /complaints/{id}/attachments  (upload)
  GET  /complaints/{id}/attachments  (list)
  GET  /attachments/{id}/download    (download)
"""
import pytest
from tests.conftest import auth_header


class TestUploadAttachment:

    def test_unsupported_file_type_returns_400(self, client, staff_token):
        """Only JPEG, PNG, PDF are allowed. A .txt upload must return 400."""
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

    def test_unauthenticated_upload_returns_401(self, client, staff_token):
        """Uploading without a token must return 401."""
        complaints = client.get(
            "/complaints/", headers=auth_header(staff_token)
        ).json()
        if not complaints:
            pytest.skip("No complaints available for test")
        unique_key = complaints[0]["unique_key"]

        r = client.post(
            f"/complaints/{unique_key}/attachments",
            files={"file": ("test.txt", b"hello", "text/plain")}
        )
        assert r.status_code == 401

    def test_upload_to_nonexistent_complaint_returns_404(self, client, staff_token):
        """Uploading to a complaint that doesn't exist must return 404."""
        r = client.post(
            "/complaints/999999999/attachments",
            files={"file": ("test.jpg", b"fakejpeg", "image/jpeg")},
            headers=auth_header(staff_token)
        )
        assert r.status_code == 404


class TestListAttachments:

    def test_authenticated_returns_200_with_attachments_key(self, client, staff_token):
        """Authenticated list must return 200 with an attachments list."""
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
        assert "total"       in r.json()

    def test_unauthenticated_returns_401(self, client, staff_token):
        """No token must return 401."""
        complaints = client.get(
            "/complaints/", headers=auth_header(staff_token)
        ).json()
        if not complaints:
            pytest.skip("No complaints available")
        unique_key = complaints[0]["unique_key"]

        r = client.get(f"/complaints/{unique_key}/attachments")
        assert r.status_code == 401

    def test_agency_isolation_nypd_cannot_see_dpr_attachments(
        self, client, staff_token, analyst_token
    ):
        """NYPD staff must not access DPR complaint attachments — agency isolation."""
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
        # either 404 (complaint not visible) or 200 with empty list
        assert r.status_code in (404, 200)
        if r.status_code == 200:
            assert r.json()["total"] == 0


class TestDownloadAttachment:

    def test_nonexistent_attachment_returns_404(self, client, staff_token):
        """Downloading an attachment ID that doesn't exist must return 404."""
        r = client.get(
            "/attachments/999999/download",
            headers=auth_header(staff_token)
        )
        assert r.status_code == 404

    def test_unauthenticated_download_returns_401(self, client):
        """No token must return 401."""
        r = client.get("/attachments/1/download")
        assert r.status_code == 401
