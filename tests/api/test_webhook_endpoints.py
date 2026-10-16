"""Tests for webhook API endpoints."""

import hashlib
import hmac
import json
import os
import time
from unittest.mock import patch

import pytest
from rest_framework import status

SECRET = "test-secret"
URL = "/webhook/update-image/"


def signed_post(client, data, secret=SECRET, timestamp=None, body=None):
    """POST ``data`` as JSON with the HMAC headers CI sends (see .github/workflows/logisim.yml)."""
    body = body if body is not None else json.dumps(data)
    timestamp = str(int(time.time())) if timestamp is None else timestamp
    sig = hmac.new(secret.encode(), f"{timestamp}.".encode() + body.encode(), hashlib.sha256)
    return client.post(
        URL,
        json.dumps(data),
        content_type="application/json",
        HTTP_X_WEBHOOK_TIMESTAMP=timestamp,
        HTTP_X_WEBHOOK_SIGNATURE=f"sha256={sig.hexdigest()}",
    )


@pytest.mark.django_db
class TestUpdateAppImageView:
    """Tests for the CI webhook endpoint that updates app image tags."""

    @pytest.fixture(autouse=True)
    def webhook_secret(self):
        with patch.dict(os.environ, {"WEBHOOK_SECRET": SECRET}):
            yield

    @pytest.fixture
    def logisim_app(self, db):
        """Create a logisim app for testing."""
        from main.models import App

        app, _ = App.objects.get_or_create(
            name="logisim",
            defaults={"image": "logisim:latest"},
        )
        return app

    def test_fails_closed_when_secret_unset(self, api_client, logisim_app):
        """An unset/empty secret must reject everything, even a request signed with ""."""
        with patch.dict(os.environ, {"WEBHOOK_SECRET": ""}):
            response = signed_post(
                api_client, {"app_name": "logisim", "image_tag": "abc123"}, secret=""
            )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        logisim_app.refresh_from_db()
        assert logisim_app.image == "logisim:latest"

    def test_unauthorized_without_signature(self, api_client, logisim_app):
        data = {"app_name": "logisim", "image_tag": "abc123"}
        response = api_client.post(URL, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"] == "Unauthorized"

    def test_unauthorized_with_wrong_secret(self, api_client, logisim_app):
        data = {"app_name": "logisim", "image_tag": "abc123"}
        response = signed_post(api_client, data, secret="wrong-secret")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_with_old_plain_secret_header(self, api_client, logisim_app):
        """The previous scheme (secret sent in clear) is no longer accepted."""
        data = {"app_name": "logisim", "image_tag": "abc123"}
        response = api_client.post(URL, data, format="json", HTTP_X_WEBHOOK_SECRET=SECRET)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_with_tampered_body(self, api_client, logisim_app):
        signed_body = json.dumps({"app_name": "logisim", "image_tag": "abc123"})
        response = signed_post(
            api_client, {"app_name": "logisim", "image_tag": "evil"}, body=signed_body
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_with_stale_timestamp(self, api_client, logisim_app):
        data = {"app_name": "logisim", "image_tag": "abc123"}
        response = signed_post(api_client, data, timestamp=str(int(time.time()) - 600))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthorized_with_non_numeric_timestamp(self, api_client, logisim_app):
        data = {"app_name": "logisim", "image_tag": "abc123"}
        response = signed_post(api_client, data, timestamp="soon")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_app_name(self, api_client, logisim_app):
        response = signed_post(api_client, {"image_tag": "abc123"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Missing app_name or image_tag"

    def test_missing_image_tag(self, api_client, logisim_app):
        response = signed_post(api_client, {"app_name": "logisim"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Missing app_name or image_tag"

    @pytest.mark.parametrize("tag", ["../x", "a b", "a:b", "-lead", "x" * 129, 123])
    def test_invalid_image_tag(self, api_client, logisim_app, tag):
        response = signed_post(api_client, {"app_name": "logisim", "image_tag": tag})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        logisim_app.refresh_from_db()
        assert logisim_app.image == "logisim:latest"

    def test_app_not_found(self, api_client):
        response = signed_post(api_client, {"app_name": "nonexistent", "image_tag": "abc123"})
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "App not found"

    def test_successful_update(self, api_client, logisim_app):
        # Same tag shape CI produces: YYYYmmdd-HHMMSS-<sha7>
        response = signed_post(
            api_client, {"app_name": "logisim", "image_tag": "20261016-142233-3addfac"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "updated"
        assert response.data["image"] == "logisim:20261016-142233-3addfac"

        logisim_app.refresh_from_db()
        assert logisim_app.image == "logisim:20261016-142233-3addfac"
