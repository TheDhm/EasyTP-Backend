from rest_framework import permissions

from main.models import DefaultUser


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or admins to access it.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Admin users have full access
        if request.user.role == DefaultUser.ADMIN or request.user.is_superuser:
            return True

        # Object owners have access
        if hasattr(obj, "user"):
            return obj.user == request.user
        if hasattr(obj, "pod_user"):
            return obj.pod_user == request.user

        return False


class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Permission for teacher-level access and above.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role in [DefaultUser.TEACHER, DefaultUser.ADMIN]
            or request.user.is_superuser
        )


class IsAdminUser(permissions.BasePermission):
    """
    Permission for admin-only access.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == DefaultUser.ADMIN or request.user.is_superuser
        )


class IsStudentOrAbove(permissions.BasePermission):
    """
    Permission for student-level access and above (excludes guests).
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in [DefaultUser.STUDENT, DefaultUser.TEACHER, DefaultUser.ADMIN]
            or request.user.is_superuser
        )


class CanAccessApp(permissions.BasePermission):
    """
    Permission to check if user can access a specific app.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Admin and teacher have access to all apps
        if (
            request.user.role in [DefaultUser.TEACHER, DefaultUser.ADMIN]
            or request.user.is_superuser
        ):
            return True

        # Check if user's group has access to the app
        app_name = view.kwargs.get("app_name")
        if app_name and request.user.group:
            return request.user.group.apps.filter(name=app_name).exists()

        return False


class RoleBasedPermission(permissions.BasePermission):
    """
    Generic role-based permission class.
    Set allowed_roles in the view to specify which roles can access it.
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Superuser always has access
        if request.user.is_superuser:
            return True

        # Check if view has defined allowed_roles
        allowed_roles = getattr(view, "allowed_roles", [])
        if not allowed_roles:
            return True  # No restrictions if no roles specified

        return request.user.role in allowed_roles
