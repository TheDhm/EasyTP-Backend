"""API tests for apps/pod endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from main.models import AccessGroup, App, DefaultUser, Pod


@pytest.fixture
def api_client():
    """Return an API client."""
    return APIClient()


@pytest.fixture
def authenticated_student_client(api_client, student_user):
    """Return an authenticated API client for student."""
    api_client.force_authenticate(user=student_user)
    return api_client


@pytest.fixture
def authenticated_teacher_client(api_client, teacher_user):
    """Return an authenticated API client for teacher."""
    api_client.force_authenticate(user=teacher_user)
    return api_client


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """Return an authenticated API client for admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def test_app(db):
    """Create a test app."""
    app, _ = App.objects.get_or_create(name="testapp", defaults={"image": "testimage:latest"})
    return app


@pytest.fixture
def student_with_app_access(db, test_app):
    """Create a student user with access to an app through their group."""
    group = AccessGroup.objects.create(name="AppAccessGroup")
    group.apps.add(test_app)

    student = DefaultUser.objects.create_user(
        username="student_with_app",
        email="student_app@test.com",
        password="testpass123",
        group=group,
        role=DefaultUser.STUDENT,
    )
    return student


@pytest.fixture
def student_pod(db, student_with_app_access, test_app):
    """Create a pod for the student."""
    pod = Pod.objects.create(
        pod_user=student_with_app_access,
        pod_name=f"testpod-{student_with_app_access.username}",
        app_name=test_app.name,
        pod_vnc_password="testvncpass",
        is_deployed=False,
    )
    return pod


class TestAppsView:
    """Tests for GET /apps/ endpoint."""

    def test_unauthenticated_access_denied(self, api_client):
        """Test unauthenticated access is denied."""
        response = api_client.get("/apps/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_sees_apps_from_their_group(
        self, api_client, student_with_app_access, test_app
    ):
        """Test student sees apps from their group."""
        api_client.force_authenticate(user=student_with_app_access)

        with patch("api.views.display_apps") as mock_display:
            mock_display.return_value = {
                test_app.name: {"name": test_app.name, "status": "stopped"}
            }

            response = api_client.get("/apps/")

            assert response.status_code == status.HTTP_200_OK
            assert "apps" in response.data
            assert response.data["user_role"] == DefaultUser.STUDENT

    def test_student_without_group_sees_no_apps(self, api_client, db):
        """Test student without group sees no apps."""
        # Create student without group
        group = AccessGroup.objects.create(name="EmptyGroup")
        student = DefaultUser.objects.create_user(
            username="student_no_apps",
            email="student_noapp@test.com",
            password="testpass123",
            group=group,
            role=DefaultUser.STUDENT,
        )
        student.group = None
        student.save()

        api_client.force_authenticate(user=student)

        with patch("api.views.display_apps") as mock_display:
            mock_display.return_value = {}

            response = api_client.get("/apps/")

            assert response.status_code == status.HTTP_200_OK
            # display_apps was called with empty queryset
            mock_display.assert_called_once()

    def test_teacher_sees_all_apps(self, authenticated_teacher_client, test_app):
        """Test teacher sees all apps."""
        with patch("api.views.display_apps") as mock_display:
            mock_display.return_value = {test_app.name: {"name": test_app.name}}

            response = authenticated_teacher_client.get("/apps/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["user_role"] == DefaultUser.TEACHER

    def test_admin_sees_all_apps(self, authenticated_admin_client, test_app):
        """Test admin sees all apps."""
        with patch("api.views.display_apps") as mock_display:
            mock_display.return_value = {test_app.name: {"name": test_app.name}}

            response = authenticated_admin_client.get("/apps/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["user_role"] == DefaultUser.ADMIN


class TestStartPodView:
    """Tests for POST /start/{app_name}/ endpoint."""

    def test_unauthenticated_access_denied(self, api_client, test_app):
        """Test unauthenticated access is denied."""
        response = api_client.post(f"/start/{test_app.name}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_without_app_access_denied(self, authenticated_student_client, test_app):
        """Test student without app access is denied by CanAccessApp permission."""
        response = authenticated_student_client.post(f"/start/{test_app.name}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_has_access_to_any_app(self, authenticated_teacher_client, test_app):
        """Test teacher has access to start any app (passes CanAccessApp)."""
        # Teacher passes permission check, but pod doesn't exist - returns 404
        response = authenticated_teacher_client.post(f"/start/{test_app.name}/")
        # Will fail at get_object_or_404 for Pod, not at permission level
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_admin_has_access_to_any_app(self, authenticated_admin_client, test_app):
        """Test admin has access to start any app (passes CanAccessApp)."""
        # Admin passes permission check, but pod doesn't exist - returns 404
        response = authenticated_admin_client.post(f"/start/{test_app.name}/")
        # Will fail at get_object_or_404 for Pod, not at permission level
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_student_with_access_can_start_pod(self, api_client, student_with_app_access, test_app):
        """Test student with group access can start pod (pod auto-created by signal)."""
        api_client.force_authenticate(user=student_with_app_access)
        # Student has access AND pod exists (created by generate_pods signal when user created)
        # Mock K8s to prevent actual deployment
        with (
            patch("api.views.deploy_app") as mock_deploy,
            patch("api.views.create_service"),
            patch("api.views.create_ingress") as mock_ingress,
            patch("api.views.stop_deployed_pod"),
        ):
            mock_ingress.return_value = "test.example.com"
            response = api_client.post(f"/start/{test_app.name}/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == "starting"
            mock_deploy.assert_called_once()


class TestStopPodView:
    """Tests for POST /stop/{app_name}/ endpoint."""

    def test_unauthenticated_access_denied(self, api_client, test_app):
        """Test unauthenticated access is denied."""
        response = api_client.post(f"/stop/{test_app.name}/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_without_app_access_denied(self, authenticated_student_client, test_app):
        """Test student without app access is denied by CanAccessApp permission."""
        response = authenticated_student_client.post(f"/stop/{test_app.name}/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_has_access_to_stop_any_app(self, authenticated_teacher_client, test_app):
        """Test teacher has access to stop any app (passes CanAccessApp)."""
        # Teacher passes permission check, but pod doesn't exist - returns 404
        response = authenticated_teacher_client.post(f"/stop/{test_app.name}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_student_with_access_can_stop_pod(self, api_client, student_with_app_access, test_app):
        """Test student with group access can stop pod (pod auto-created by signal)."""
        api_client.force_authenticate(user=student_with_app_access)
        # Student has access AND pod exists (created by generate_pods signal when user created)
        # First deploy the pod, then stop it
        from main.models import Pod

        pod = Pod.objects.get(pod_user=student_with_app_access, app_name=test_app.name)
        pod.is_deployed = True
        pod.save()

        # Mock K8s client and config to prevent actual operations
        with (
            patch("api.views.load_k8s_config"),
            patch("kubernetes.client") as mock_k8s_client,
            patch("api.views.delete_ingress"),
        ):
            mock_apps_api = MagicMock()
            mock_core_api = MagicMock()
            mock_k8s_client.AppsV1Api.return_value = mock_apps_api
            mock_k8s_client.CoreV1Api.return_value = mock_core_api

            response = api_client.post(f"/stop/{test_app.name}/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == "stopped"
            mock_apps_api.delete_namespaced_deployment.assert_called_once()


class TestDashboardView:
    """Tests for GET /dashboard/ endpoint."""

    def test_unauthenticated_access_denied(self, api_client):
        """Test unauthenticated access is denied."""
        response = api_client.get("/dashboard/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_dashboard(self, authenticated_student_client, student_user):
        """Test student dashboard returns correct data."""
        with patch("api.views.get_sub_files_secure", return_value=([], [])):
            response = authenticated_student_client.get("/dashboard/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["template_type"] == "student_home"
            assert response.data["role"] == DefaultUser.STUDENT
            assert "running_apps" in response.data
            assert "total_files" in response.data
            assert "storage_used" in response.data

    def test_teacher_dashboard(self, authenticated_teacher_client, teacher_user):
        """Test teacher dashboard returns correct data."""
        with patch("api.views.get_sub_files_secure", return_value=([], [])):
            response = authenticated_teacher_client.get("/dashboard/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["template_type"] == "teacher_home"
            assert response.data["role"] == DefaultUser.TEACHER

    def test_admin_dashboard(self, authenticated_admin_client, admin_user):
        """Test admin dashboard returns correct data."""
        with patch("api.views.get_sub_files_secure", return_value=([], [])):
            response = authenticated_admin_client.get("/dashboard/")

            assert response.status_code == status.HTTP_200_OK
            assert response.data["template_type"] == "admin"
            assert response.data["role"] == DefaultUser.ADMIN
