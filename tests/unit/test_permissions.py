"""Unit tests for api.permissions module."""
import pytest
from unittest.mock import MagicMock, Mock
from rest_framework.test import APIRequestFactory

from api.permissions import (
    IsOwnerOrAdmin,
    IsTeacherOrAdmin,
    IsAdminUser,
    IsStudentOrAbove,
    CanAccessApp,
    RoleBasedPermission,
)


@pytest.fixture
def request_factory():
    """Return an API request factory."""
    return APIRequestFactory()


@pytest.fixture
def mock_view():
    """Return a mock view."""
    view = MagicMock()
    view.kwargs = {}
    return view


class TestIsOwnerOrAdmin:
    """Tests for IsOwnerOrAdmin permission."""

    def test_unauthenticated_user_denied(self, request_factory, mock_view):
        """Test unauthenticated user is denied."""
        permission = IsOwnerOrAdmin()
        request = request_factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        assert permission.has_permission(request, mock_view) is False

    def test_authenticated_user_allowed_at_view_level(self, request_factory, mock_view):
        """Test authenticated user passes view-level permission."""
        permission = IsOwnerOrAdmin()
        request = request_factory.get('/')
        request.user = MagicMock(is_authenticated=True)

        assert permission.has_permission(request, mock_view) is True

    def test_admin_user_has_object_permission(self, request_factory, mock_view, admin_user):
        """Test admin user has object permission."""
        permission = IsOwnerOrAdmin()
        request = request_factory.get('/')
        request.user = admin_user

        # Create an object owned by someone else
        obj = MagicMock()
        obj.user = MagicMock()

        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_superuser_has_object_permission(self, request_factory, mock_view, db):
        """Test superuser has object permission."""
        from main.models import DefaultUser, AccessGroup
        group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
        superuser = DefaultUser.objects.create_user(
            username='superuser_test',
            email='super@test.com',
            password='pass123',
            group=group,
            is_superuser=True,
        )

        permission = IsOwnerOrAdmin()
        request = request_factory.get('/')
        request.user = superuser

        obj = MagicMock()
        obj.user = MagicMock()

        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_owner_has_object_permission_via_user_field(self, request_factory, mock_view, student_user):
        """Test owner has permission via user field."""
        permission = IsOwnerOrAdmin()
        request = request_factory.get('/')
        request.user = student_user

        obj = MagicMock()
        obj.user = student_user

        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_owner_has_object_permission_via_pod_user_field(self, request_factory, mock_view, student_user):
        """Test owner has permission via pod_user field."""
        permission = IsOwnerOrAdmin()
        request = request_factory.get('/')
        request.user = student_user

        obj = MagicMock(spec=['pod_user'])
        obj.pod_user = student_user
        # Remove user attribute
        del obj.user

        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_non_owner_denied(self, request_factory, mock_view, student_user, teacher_user):
        """Test non-owner is denied."""
        permission = IsOwnerOrAdmin()
        request = request_factory.get('/')
        request.user = student_user

        obj = MagicMock()
        obj.user = teacher_user

        assert permission.has_object_permission(request, mock_view, obj) is False


class TestIsTeacherOrAdmin:
    """Tests for IsTeacherOrAdmin permission."""

    def test_unauthenticated_user_denied(self, request_factory, mock_view):
        """Test unauthenticated user is denied."""
        permission = IsTeacherOrAdmin()
        request = request_factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        assert permission.has_permission(request, mock_view) is False

    def test_student_denied(self, request_factory, mock_view, student_user):
        """Test student is denied."""
        permission = IsTeacherOrAdmin()
        request = request_factory.get('/')
        request.user = student_user

        assert permission.has_permission(request, mock_view) is False

    def test_guest_denied(self, request_factory, mock_view, guest_user):
        """Test guest is denied."""
        permission = IsTeacherOrAdmin()
        request = request_factory.get('/')
        request.user = guest_user

        assert permission.has_permission(request, mock_view) is False

    def test_teacher_allowed(self, request_factory, mock_view, teacher_user):
        """Test teacher is allowed."""
        permission = IsTeacherOrAdmin()
        request = request_factory.get('/')
        request.user = teacher_user

        assert permission.has_permission(request, mock_view) is True

    def test_admin_allowed(self, request_factory, mock_view, admin_user):
        """Test admin is allowed."""
        permission = IsTeacherOrAdmin()
        request = request_factory.get('/')
        request.user = admin_user

        assert permission.has_permission(request, mock_view) is True

    def test_superuser_allowed(self, request_factory, mock_view, db):
        """Test superuser is allowed."""
        from main.models import DefaultUser, AccessGroup
        group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
        superuser = DefaultUser.objects.create_user(
            username='superuser_teacher_test',
            email='super_teach@test.com',
            password='pass123',
            group=group,
            role=DefaultUser.STUDENT,  # Even with student role
            is_superuser=True,
        )

        permission = IsTeacherOrAdmin()
        request = request_factory.get('/')
        request.user = superuser

        assert permission.has_permission(request, mock_view) is True


class TestIsAdminUser:
    """Tests for IsAdminUser permission."""

    def test_unauthenticated_user_denied(self, request_factory, mock_view):
        """Test unauthenticated user is denied."""
        permission = IsAdminUser()
        request = request_factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        assert permission.has_permission(request, mock_view) is False

    def test_student_denied(self, request_factory, mock_view, student_user):
        """Test student is denied."""
        permission = IsAdminUser()
        request = request_factory.get('/')
        request.user = student_user

        assert permission.has_permission(request, mock_view) is False

    def test_teacher_denied(self, request_factory, mock_view, teacher_user):
        """Test teacher is denied."""
        permission = IsAdminUser()
        request = request_factory.get('/')
        request.user = teacher_user

        assert permission.has_permission(request, mock_view) is False

    def test_admin_allowed(self, request_factory, mock_view, admin_user):
        """Test admin is allowed."""
        permission = IsAdminUser()
        request = request_factory.get('/')
        request.user = admin_user

        assert permission.has_permission(request, mock_view) is True

    def test_superuser_allowed(self, request_factory, mock_view, db):
        """Test superuser is allowed."""
        from main.models import DefaultUser, AccessGroup
        group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
        superuser = DefaultUser.objects.create_user(
            username='superuser_admin_test',
            email='super_admin@test.com',
            password='pass123',
            group=group,
            role=DefaultUser.STUDENT,
            is_superuser=True,
        )

        permission = IsAdminUser()
        request = request_factory.get('/')
        request.user = superuser

        assert permission.has_permission(request, mock_view) is True


class TestIsStudentOrAbove:
    """Tests for IsStudentOrAbove permission."""

    def test_unauthenticated_user_denied(self, request_factory, mock_view):
        """Test unauthenticated user is denied."""
        permission = IsStudentOrAbove()
        request = request_factory.get('/')
        request.user = MagicMock(is_authenticated=False, is_superuser=False)

        assert permission.has_permission(request, mock_view) is False

    def test_guest_denied(self, request_factory, mock_view, guest_user):
        """Test guest is denied."""
        permission = IsStudentOrAbove()
        request = request_factory.get('/')
        request.user = guest_user

        assert permission.has_permission(request, mock_view) is False

    def test_student_allowed(self, request_factory, mock_view, student_user):
        """Test student is allowed."""
        permission = IsStudentOrAbove()
        request = request_factory.get('/')
        request.user = student_user

        assert permission.has_permission(request, mock_view) is True

    def test_teacher_allowed(self, request_factory, mock_view, teacher_user):
        """Test teacher is allowed."""
        permission = IsStudentOrAbove()
        request = request_factory.get('/')
        request.user = teacher_user

        assert permission.has_permission(request, mock_view) is True

    def test_admin_allowed(self, request_factory, mock_view, admin_user):
        """Test admin is allowed."""
        permission = IsStudentOrAbove()
        request = request_factory.get('/')
        request.user = admin_user

        assert permission.has_permission(request, mock_view) is True


class TestCanAccessApp:
    """Tests for CanAccessApp permission."""

    def test_unauthenticated_user_denied(self, request_factory, mock_view):
        """Test unauthenticated user is denied."""
        permission = CanAccessApp()
        request = request_factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        assert permission.has_permission(request, mock_view) is False

    def test_admin_can_access_all_apps(self, request_factory, mock_view, admin_user):
        """Test admin can access all apps."""
        permission = CanAccessApp()
        request = request_factory.get('/')
        request.user = admin_user
        mock_view.kwargs = {'app_name': 'any_app'}

        assert permission.has_permission(request, mock_view) is True

    def test_teacher_can_access_all_apps(self, request_factory, mock_view, teacher_user):
        """Test teacher can access all apps."""
        permission = CanAccessApp()
        request = request_factory.get('/')
        request.user = teacher_user
        mock_view.kwargs = {'app_name': 'any_app'}

        assert permission.has_permission(request, mock_view) is True

    def test_student_can_access_assigned_app(self, request_factory, mock_view, db):
        """Test student can access app assigned to their group."""
        from main.models import DefaultUser, AccessGroup, App

        # Create group with app
        group = AccessGroup.objects.create(name='StudentGroupWithApp')
        app = App.objects.create(name='testapp', image='test:latest')
        group.apps.add(app)

        # Create student in this group
        student = DefaultUser.objects.create_user(
            username='student_with_app',
            email='student_app@test.com',
            password='pass123',
            group=group,
            role=DefaultUser.STUDENT,
        )

        permission = CanAccessApp()
        request = request_factory.get('/')
        request.user = student
        mock_view.kwargs = {'app_name': 'testapp'}

        assert permission.has_permission(request, mock_view) is True

    def test_student_cannot_access_unassigned_app(self, request_factory, mock_view, db):
        """Test student cannot access app not assigned to their group."""
        from main.models import DefaultUser, AccessGroup, App

        # Create group without app
        group = AccessGroup.objects.create(name='StudentGroupWithoutApp')

        # Create student in this group
        student = DefaultUser.objects.create_user(
            username='student_without_app',
            email='student_noapp@test.com',
            password='pass123',
            group=group,
            role=DefaultUser.STUDENT,
        )

        permission = CanAccessApp()
        request = request_factory.get('/')
        request.user = student
        mock_view.kwargs = {'app_name': 'unassigned_app'}

        assert permission.has_permission(request, mock_view) is False

    def test_student_without_group_denied(self, request_factory, mock_view, db):
        """Test student without group is denied."""
        from main.models import DefaultUser, AccessGroup

        # Create student without group
        group = AccessGroup.objects.create(name='TempGroup')
        student = DefaultUser.objects.create_user(
            username='student_no_group',
            email='student_nogroup@test.com',
            password='pass123',
            group=group,
            role=DefaultUser.STUDENT,
        )
        student.group = None
        student.save()

        permission = CanAccessApp()
        request = request_factory.get('/')
        request.user = student
        mock_view.kwargs = {'app_name': 'some_app'}

        assert permission.has_permission(request, mock_view) is False


class TestRoleBasedPermission:
    """Tests for RoleBasedPermission."""

    def test_unauthenticated_user_denied(self, request_factory, mock_view):
        """Test unauthenticated user is denied."""
        permission = RoleBasedPermission()
        request = request_factory.get('/')
        request.user = MagicMock(is_authenticated=False)

        assert permission.has_permission(request, mock_view) is False

    def test_superuser_always_allowed(self, request_factory, db):
        """Test superuser always has access."""
        from main.models import DefaultUser, AccessGroup

        group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
        superuser = DefaultUser.objects.create_user(
            username='superuser_role_test',
            email='super_role@test.com',
            password='pass123',
            group=group,
            role=DefaultUser.GUEST,  # Even with guest role
            is_superuser=True,
        )

        permission = RoleBasedPermission()
        request = APIRequestFactory().get('/')
        request.user = superuser

        # View with restrictive allowed_roles
        view = MagicMock()
        view.allowed_roles = [DefaultUser.ADMIN]

        assert permission.has_permission(request, view) is True

    def test_no_allowed_roles_allows_all(self, request_factory, mock_view, student_user):
        """Test no allowed_roles defined allows all authenticated users."""
        permission = RoleBasedPermission()
        request = request_factory.get('/')
        request.user = student_user
        mock_view.allowed_roles = []

        assert permission.has_permission(request, mock_view) is True

    def test_user_role_in_allowed_roles(self, request_factory, mock_view, student_user):
        """Test user with role in allowed_roles is allowed."""
        from main.models import DefaultUser

        permission = RoleBasedPermission()
        request = request_factory.get('/')
        request.user = student_user
        mock_view.allowed_roles = [DefaultUser.STUDENT, DefaultUser.TEACHER]

        assert permission.has_permission(request, mock_view) is True

    def test_user_role_not_in_allowed_roles(self, request_factory, mock_view, student_user):
        """Test user with role not in allowed_roles is denied."""
        from main.models import DefaultUser

        permission = RoleBasedPermission()
        request = request_factory.get('/')
        request.user = student_user
        mock_view.allowed_roles = [DefaultUser.ADMIN, DefaultUser.TEACHER]

        assert permission.has_permission(request, mock_view) is False