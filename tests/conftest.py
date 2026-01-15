"""Shared test fixtures for pytest."""
import pytest
from unittest.mock import patch, MagicMock
from django.test import Client
from rest_framework.test import APIClient

import factory
from factory.django import DjangoModelFactory


@pytest.fixture(autouse=True)
def block_k8s_calls():
    """Block all real K8s API calls during tests. Autouse ensures this runs for every test."""
    with patch('kubernetes.client.CoreV1Api') as mock_core, \
         patch('kubernetes.client.AppsV1Api') as mock_apps, \
         patch('kubernetes.client.NetworkingV1Api') as mock_net, \
         patch('kubernetes.config.load_kube_config') as mock_kube_cfg, \
         patch('kubernetes.config.load_incluster_config') as mock_cluster_cfg:
        # Make the mocks raise if accidentally called without explicit mocking
        mock_core.return_value.create_namespaced_service.side_effect = RuntimeError("K8s not mocked")
        mock_apps.return_value.create_namespaced_deployment.side_effect = RuntimeError("K8s not mocked")
        mock_apps.return_value.delete_namespaced_deployment.side_effect = RuntimeError("K8s not mocked")
        yield


@pytest.fixture
def api_client():
    """Return an API client for testing DRF endpoints."""
    return APIClient()


@pytest.fixture
def django_client():
    """Return a Django test client."""
    return Client()


@pytest.fixture
def mock_k8s_config():
    """Mock Kubernetes configuration loading."""
    with patch('shared.kubernetes.config.config') as mock_config:
        mock_config.load_kube_config = MagicMock()
        mock_config.load_incluster_config = MagicMock()
        yield mock_config


@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes client APIs."""
    with patch('kubernetes.client') as mock_client:
        # Mock CoreV1Api
        mock_core_api = MagicMock()
        mock_client.CoreV1Api.return_value = mock_core_api

        # Mock AppsV1Api
        mock_apps_api = MagicMock()
        mock_client.AppsV1Api.return_value = mock_apps_api

        # Mock NetworkingV1Api
        mock_networking_api = MagicMock()
        mock_client.NetworkingV1Api.return_value = mock_networking_api

        yield {
            'client': mock_client,
            'core_api': mock_core_api,
            'apps_api': mock_apps_api,
            'networking_api': mock_networking_api,
        }


# User factories - import models lazily to avoid Django setup issues
@pytest.fixture
def access_group_factory():
    """Factory for creating access groups."""
    from main.models import AccessGroup

    class AccessGroupFactory(DjangoModelFactory):
        class Meta:
            model = AccessGroup
            django_get_or_create = ('name',)
        name = factory.Sequence(lambda n: f'group_{n}')

    return AccessGroupFactory


@pytest.fixture
def user_factory():
    """Factory for creating users."""
    from main.models import DefaultUser, AccessGroup

    class UserFactory(DjangoModelFactory):
        class Meta:
            model = DefaultUser
            django_get_or_create = ('username',)
        username = factory.Sequence(lambda n: f'user_{n}')
        email = factory.LazyAttribute(lambda obj: f'{obj.username}@example.com')
        is_active = True

        @factory.lazy_attribute
        def group(self):
            group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
            return group

        @classmethod
        def _create(cls, model_class, *args, **kwargs):
            password = kwargs.pop('password', 'testpass123')
            obj = super()._create(model_class, *args, **kwargs)
            obj.set_password(password)
            obj.save()
            return obj

    return UserFactory


# Fixtures that use factories
@pytest.fixture
def access_group(db):
    """Create a test access group."""
    from main.models import AccessGroup
    group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
    return group


@pytest.fixture
def student_user(db):
    """Create a student user."""
    from main.models import DefaultUser, AccessGroup
    group, _ = AccessGroup.objects.get_or_create(name=AccessGroup.CP1)
    user = DefaultUser.objects.create_user(
        username='test_student',
        email='student@example.com',
        password='testpass123',
        group=group,
        role=DefaultUser.STUDENT,
    )
    return user


@pytest.fixture
def teacher_user(db):
    """Create a teacher user."""
    from main.models import DefaultUser, AccessGroup
    group, _ = AccessGroup.objects.get_or_create(name=AccessGroup.FULL)
    user = DefaultUser.objects.create_user(
        username='test_teacher',
        email='teacher@example.com',
        password='testpass123',
        group=group,
        role=DefaultUser.TEACHER,
    )
    return user


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    from main.models import DefaultUser, AccessGroup
    group, _ = AccessGroup.objects.get_or_create(name=AccessGroup.FULL)
    user = DefaultUser.objects.create_user(
        username='test_admin',
        email='admin@example.com',
        password='testpass123',
        group=group,
        role=DefaultUser.ADMIN,
        is_superuser=True,
    )
    return user


@pytest.fixture
def guest_user(db):
    """Create a guest user."""
    from main.models import DefaultUser, AccessGroup
    group, _ = AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)
    user = DefaultUser.objects.create_user(
        username='test_guest',
        email='guest@example.com',
        password='testpass123',
        group=group,
        role=DefaultUser.GUEST,
    )
    return user


@pytest.fixture
def test_app(db):
    """Create a test app."""
    from main.models import App
    app, _ = App.objects.get_or_create(
        name='testapp',
        defaults={
            'image': 'test-image:latest',
            'description': 'Test application',
        }
    )
    return app


@pytest.fixture
def test_pod(db, student_user, test_app):
    """Create a test pod."""
    from main.models import Pod
    pod = Pod.objects.create(
        pod_user=student_user,
        pod_name='test-pod-hash',
        app_name=test_app.name,
        pod_vnc_user='vncuser',
        pod_vnc_password='vncpass',
        pod_namespace='apps',
    )
    return pod


@pytest.fixture
def authenticated_api_client(api_client, student_user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=student_user)
    return api_client


@pytest.fixture
def teacher_api_client(api_client, teacher_user):
    """Return an API client authenticated as teacher."""
    api_client.force_authenticate(user=teacher_user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """Return an API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def temp_user_dir(tmp_path, student_user):
    """Create a temporary user directory for file operations."""
    user_dir = tmp_path / 'USERDATA' / student_user.username
    user_dir.mkdir(parents=True)
    return user_dir