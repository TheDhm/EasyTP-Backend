"""Tests for webhook API endpoints."""

import os
from unittest.mock import patch

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestUpdateAppImageView:
    """Tests for the CI webhook endpoint that updates app image tags."""

    @pytest.fixture
    def logisim_app(self, db):
        """Create a logisim app for testing."""
        from main.models import App

        app, _ = App.objects.get_or_create(
            name="logisim",
            defaults={"image": "logisim:latest"},
        )
        return app

    def test_unauthorized_without_secret(self, api_client, logisim_app):
        """Test that requests without webhook secret header are rejected."""
        with patch.dict(os.environ, {"WEBHOOK_SECRET": "required-secret"}):
            data = {"app_name": "logisim", "image_tag": "abc123"}
            response = api_client.post("/webhook/update-image/", data, format="json")
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.data["error"] == "Unauthorized"

    def test_unauthorized_with_wrong_secret(self, api_client, logisim_app):
        """Test that requests with wrong webhook secret are rejected."""
        with patch.dict(os.environ, {"WEBHOOK_SECRET": "correct-secret"}):
            data = {"app_name": "logisim", "image_tag": "abc123"}
            response = api_client.post(
                "/webhook/update-image/",
                data,
                format="json",
                HTTP_X_WEBHOOK_SECRET="wrong-secret",
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert response.data["error"] == "Unauthorized"

    def test_missing_app_name(self, api_client, logisim_app):
        """Test that requests without app_name are rejected."""
        with patch.dict(os.environ, {"WEBHOOK_SECRET": "test-secret"}):
            data = {"image_tag": "abc123"}
            response = api_client.post(
                "/webhook/update-image/",
                data,
                format="json",
                HTTP_X_WEBHOOK_SECRET="test-secret",
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data["error"] == "Missing app_name or image_tag"

    def test_missing_image_tag(self, api_client, logisim_app):
        """Test that requests without image_tag are rejected."""
        with patch.dict(os.environ, {"WEBHOOK_SECRET": "test-secret"}):
            data = {"app_name": "logisim"}
            response = api_client.post(
                "/webhook/update-image/",
                data,
                format="json",
                HTTP_X_WEBHOOK_SECRET="test-secret",
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.data["error"] == "Missing app_name or image_tag"

    def test_app_not_found(self, api_client):
        """Test that requests for non-existent apps return 404."""
        with patch.dict(os.environ, {"WEBHOOK_SECRET": "test-secret"}):
            data = {"app_name": "nonexistent", "image_tag": "abc123"}
            response = api_client.post(
                "/webhook/update-image/",
                data,
                format="json",
                HTTP_X_WEBHOOK_SECRET="test-secret",
            )
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert response.data["error"] == "App not found"

    def test_successful_update(self, api_client, logisim_app):
        """Test successful image tag update."""

        with patch.dict(os.environ, {"WEBHOOK_SECRET": "test-secret"}):
            data = {"app_name": "logisim", "image_tag": "abc123def456"}
            response = api_client.post(
                "/webhook/update-image/",
                data,
                format="json",
                HTTP_X_WEBHOOK_SECRET="test-secret",
            )
            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == "updated"
            assert response.data["image"] == "logisim:abc123def456"

            # Verify the app was actually updated in the database
            logisim_app.refresh_from_db()
            assert logisim_app.image == "logisim:abc123def456"

    def test_update_preserves_app_name_in_image(self, api_client, logisim_app):
        """Test that the image tag is formatted as app_name:tag."""

        with patch.dict(os.environ, {"WEBHOOK_SECRET": "test-secret"}):
            data = {"app_name": "logisim", "image_tag": "sha256abcdef"}
            response = api_client.post(
                "/webhook/update-image/",
                data,
                format="json",
                HTTP_X_WEBHOOK_SECRET="test-secret",
            )
            assert response.status_code == status.HTTP_200_OK

            # Verify the format is app_name:tag
            logisim_app.refresh_from_db()
            assert logisim_app.image == "logisim:sha256abcdef"
