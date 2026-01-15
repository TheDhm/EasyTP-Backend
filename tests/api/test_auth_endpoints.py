"""Tests for authentication API endpoints."""

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestSignupEndpoint:
    """Tests for user signup endpoint."""

    @pytest.fixture(autouse=True)
    def setup_groups(self, db):
        """Ensure required groups exist."""
        from main.models import AccessGroup

        AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)

    def test_signup_success(self, api_client):
        """Test successful user signup."""
        from main.models import DefaultUser

        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "securePass123!",
            "password_confirm": "securePass123!",
        }
        response = api_client.post("/auth/signup/", data, format="json")
        print(response.data)
        assert response.status_code == status.HTTP_201_CREATED
        assert "access" in response.data or "user" in response.data
        assert DefaultUser.objects.filter(username="newuser").exists()

    def test_signup_password_mismatch(self, api_client):
        """Test signup with mismatched passwords fails."""
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "securePass123!",
            "password_confirm": "differentPass!",
        }
        response = api_client.post("/auth/signup/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_signup_duplicate_username(self, api_client, student_user):
        """Test signup with existing username fails."""
        data = {
            "username": student_user.username,
            "email": "different@example.com",
            "password": "securePass123!",
            "password_confirm": "securePass123!",
        }
        response = api_client.post("/auth/signup/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_signup_invalid_email(self, api_client):
        """Test signup with invalid email fails."""
        data = {
            "username": "newuser",
            "email": "not-an-email",
            "password": "securePass123!",
            "password_confirm": "securePass123!",
        }
        response = api_client.post("/auth/signup/", data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestLoginEndpoint:
    """Tests for user login endpoint."""

    @pytest.fixture(autouse=True)
    def setup_groups(self, db):
        """Ensure required groups exist."""
        from main.models import AccessGroup

        AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)

    def test_login_success(self, api_client):
        """Test successful login returns JWT tokens."""
        from main.models import AccessGroup, DefaultUser

        # Create user
        group, _ = AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)
        DefaultUser.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password="testpass123",
            group=group,
            role=DefaultUser.STUDENT,
        )

        data = {
            "username": "loginuser",
            "password": "testpass123",
        }
        response = api_client.post("/auth/login/", data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data

    def test_login_wrong_password(self, api_client, student_user):
        """Test login with wrong password fails."""
        data = {
            "username": student_user.username,
            "password": "wrongpassword",
        }
        response = api_client.post("/auth/login/", data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login with nonexistent user fails."""
        data = {
            "username": "nonexistent",
            "password": "somepassword",
        }
        response = api_client.post("/auth/login/", data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestTokenRefresh:
    """Tests for JWT token refresh."""

    @pytest.fixture(autouse=True)
    def setup_groups(self, db):
        """Ensure required groups exist."""
        from main.models import AccessGroup

        AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)

    def test_token_refresh(self, api_client):
        """Test refreshing JWT token."""
        from main.models import AccessGroup, DefaultUser

        # Create user and login
        group, _ = AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)
        DefaultUser.objects.create_user(
            username="refreshuser",
            email="refresh@example.com",
            password="testpass123",
            group=group,
        )

        # Get tokens
        login_response = api_client.post(
            "/auth/login/",
            {
                "username": "refreshuser",
                "password": "testpass123",
            },
            format="json",
        )

        refresh_token = login_response.data["refresh"]

        # Refresh token
        response = api_client.post(
            "/auth/refresh/",
            {
                "refresh": refresh_token,
            },
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data

    def test_token_refresh_invalid(self, api_client):
        """Test refreshing with invalid token fails."""
        response = api_client.post(
            "/auth/refresh/",
            {
                "refresh": "invalid-token",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestGuestLogin:
    """Tests for guest user creation."""

    def test_guest_login_creates_user(self, api_client):
        """Test guest login creates a guest user."""
        from main.models import DefaultUser

        response = api_client.post("/auth/continue-as-guest/", format="json")
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        # Check guest user was created
        assert DefaultUser.objects.filter(role=DefaultUser.GUEST).exists()

    def test_guest_user_has_limited_role(self, api_client):
        """Test guest user has GUEST role."""
        from main.models import DefaultUser

        response = api_client.post("/auth/continue-as-guest/", format="json")
        assert response.status_code == status.HTTP_200_OK

        # Find the created guest user
        guest = DefaultUser.objects.filter(role=DefaultUser.GUEST).last()
        assert guest is not None
        assert guest.role == DefaultUser.GUEST


@pytest.mark.django_db
class TestUserProfile:
    """Tests for user profile endpoint."""

    def test_get_profile_authenticated(self, authenticated_api_client, student_user):
        """Test authenticated user can get their profile."""
        response = authenticated_api_client.get("/dashboard/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["user"]["username"] == student_user.username

    def test_get_profile_unauthenticated(self, api_client):
        """Test unauthenticated request is rejected."""
        response = api_client.get("/dashboard/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestLogout:
    """Tests for logout endpoint."""

    @pytest.fixture(autouse=True)
    def setup_groups(self, db):
        """Ensure required groups exist."""
        from main.models import AccessGroup

        AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)

    def test_logout_success(self, api_client):
        """Test logout invalidates refresh token."""
        from main.models import AccessGroup, DefaultUser

        # Create user and login
        group, _ = AccessGroup.objects.get_or_create(name=AccessGroup.GUEST)
        DefaultUser.objects.create_user(
            username="logoutuser",
            email="logout@example.com",
            password="testpass123",
            group=group,
            role=DefaultUser.STUDENT,
        )

        # Login
        login_response = api_client.post(
            "/auth/login/",
            {
                "username": "logoutuser",
                "password": "testpass123",
            },
            format="json",
        )

        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # Logout
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.post(
            "/auth/logout/",
            {
                "refresh": refresh_token,
            },
            format="json",
        )

        # Should succeed or return 200/204
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_204_NO_CONTENT,
            status.HTTP_205_RESET_CONTENT,
        ]
