"""Unit tests for api.serializers module."""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from api.serializers import (
    SignupSerializer,
    LoginSerializer,
    FileUploadSerializer,
)
from main.models import DefaultUser, AccessGroup


class TestSignupSerializer:
    """Tests for SignupSerializer validation."""

    @pytest.fixture
    def valid_signup_data(self, db):
        """Return valid signup data."""
        return {
            'email': 'newuser@example.com',
            'username': 'newuser',
            'password': 'SecurePass123!',
            'password_confirm': 'SecurePass123!',
        }

    def test_valid_signup_data(self, valid_signup_data):
        """Test serializer accepts valid data."""
        serializer = SignupSerializer(data=valid_signup_data)
        assert serializer.is_valid(), serializer.errors

    def test_reserved_username_rejected(self, valid_signup_data):
        """Test reserved usernames are rejected."""
        reserved_names = ['admin', 'root', 'system', 'api', 'www']
        for name in reserved_names:
            data = valid_signup_data.copy()
            data['username'] = name
            serializer = SignupSerializer(data=data)
            assert not serializer.is_valid()
            assert 'username' in serializer.errors
            assert 'reserved' in str(serializer.errors['username'][0]).lower()

    def test_reserved_username_case_insensitive(self, valid_signup_data):
        """Test reserved username check is case-insensitive."""
        data = valid_signup_data.copy()
        data['username'] = 'ADMIN'  # Uppercase version
        serializer = SignupSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors

    def test_username_invalid_characters_rejected(self, valid_signup_data):
        """Test usernames with invalid characters are rejected."""
        data = valid_signup_data.copy()
        data['username'] = 'user@name!'  # Invalid chars
        serializer = SignupSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors
        assert 'can only contain' in str(serializer.errors['username'][0])

    def test_username_too_short_rejected(self, valid_signup_data):
        """Test usernames under 3 characters are rejected."""
        data = valid_signup_data.copy()
        data['username'] = 'ab'  # Too short
        serializer = SignupSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors
        assert 'at least 3 characters' in str(serializer.errors['username'][0])

    def test_username_too_long_rejected(self, valid_signup_data):
        """Test usernames over 30 characters are rejected."""
        data = valid_signup_data.copy()
        data['username'] = 'a' * 31  # Too long
        serializer = SignupSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors
        assert 'no more than 30' in str(serializer.errors['username'][0])

    def test_password_mismatch_rejected(self, valid_signup_data):
        """Test mismatched passwords are rejected."""
        data = valid_signup_data.copy()
        data['password_confirm'] = 'DifferentPass!'
        serializer = SignupSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors

    def test_duplicate_username_rejected(self, valid_signup_data, db):
        """Test duplicate usernames are rejected."""
        # Create existing user
        group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
        DefaultUser.objects.create_user(
            username='existinguser',
            email='existing@example.com',
            password='pass123',
            group=group,
        )

        data = valid_signup_data.copy()
        data['username'] = 'existinguser'
        serializer = SignupSerializer(data=data)
        assert not serializer.is_valid()
        assert 'username' in serializer.errors
        assert 'already exists' in str(serializer.errors['username'][0])

    def test_username_with_hyphen_allowed(self, valid_signup_data):
        """Test usernames with hyphens are allowed."""
        data = valid_signup_data.copy()
        data['username'] = 'user-name'
        serializer = SignupSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_username_with_underscore_allowed(self, valid_signup_data):
        """Test usernames with underscores are allowed."""
        data = valid_signup_data.copy()
        data['username'] = 'user_name'
        serializer = SignupSerializer(data=data)
        assert serializer.is_valid(), serializer.errors

    def test_signup_creates_user_with_guest_group(self, valid_signup_data, db):
        """Test signup creates user with Guest group by default."""
        serializer = SignupSerializer(data=valid_signup_data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.group.name == AccessGroup.GUEST

    def test_guest_role_gets_guest_group(self, valid_signup_data, db):
        """Test guest role users get assigned to Guest group."""
        data = valid_signup_data.copy()
        data['role'] = DefaultUser.GUEST
        serializer = SignupSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        user = serializer.save()
        assert user.group.name == AccessGroup.GUEST


class TestLoginSerializer:
    """Tests for LoginSerializer validation."""

    @pytest.fixture
    def active_user(self, db):
        """Create an active user for login tests."""
        group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
        return DefaultUser.objects.create_user(
            username='activeuser',
            email='active@example.com',
            password='testpass123',
            group=group,
            is_active=True,
        )

    @pytest.fixture
    def inactive_user(self, db):
        """Create an inactive user for login tests."""
        group, _ = AccessGroup.objects.get_or_create(name='TestGroup')
        return DefaultUser.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='testpass123',
            group=group,
            is_active=False,
        )

    def test_valid_credentials_accepted(self, active_user):
        """Test valid credentials are accepted."""
        serializer = LoginSerializer(data={
            'username': 'activeuser',
            'password': 'testpass123',
        })
        assert serializer.is_valid(), serializer.errors
        assert 'user' in serializer.validated_data

    def test_invalid_credentials_rejected(self, active_user):
        """Test invalid credentials are rejected."""
        serializer = LoginSerializer(data={
            'username': 'activeuser',
            'password': 'wrongpassword',
        })
        assert not serializer.is_valid()
        assert 'Invalid credentials' in str(serializer.errors)

    def test_inactive_user_rejected(self, inactive_user):
        """Test inactive users cannot login."""
        serializer = LoginSerializer(data={
            'username': 'inactiveuser',
            'password': 'testpass123',
        })
        # Django's authenticate() returns None for inactive users, so error is 'Invalid credentials'
        assert not serializer.is_valid()
        assert 'invalid credentials' in str(serializer.errors).lower()

    def test_missing_username_rejected(self, active_user):
        """Test missing username is rejected."""
        serializer = LoginSerializer(data={
            'password': 'testpass123',
        })
        assert not serializer.is_valid()

    def test_missing_password_rejected(self, active_user):
        """Test missing password is rejected."""
        serializer = LoginSerializer(data={
            'username': 'activeuser',
        })
        assert not serializer.is_valid()

    def test_empty_credentials_rejected(self):
        """Test empty credentials are rejected."""
        serializer = LoginSerializer(data={
            'username': '',
            'password': '',
        })
        assert not serializer.is_valid()


class TestFileUploadSerializer:
    """Tests for FileUploadSerializer validation."""

    def test_valid_file_accepted(self):
        """Test valid file under 10MB is accepted."""
        content = b'x' * (5 * 1024 * 1024)  # 5MB
        file = SimpleUploadedFile('test.txt', content, content_type='text/plain')
        serializer = FileUploadSerializer(data={'file': file})
        assert serializer.is_valid(), serializer.errors

    def test_file_over_10mb_rejected(self):
        """Test files over 10MB are rejected."""
        content = b'x' * (11 * 1024 * 1024)  # 11MB
        file = SimpleUploadedFile('large.txt', content, content_type='text/plain')
        serializer = FileUploadSerializer(data={'file': file})
        assert not serializer.is_valid()
        assert 'file' in serializer.errors
        assert '10MB' in str(serializer.errors['file'][0])

    def test_exactly_10mb_file_accepted(self):
        """Test file exactly 10MB is accepted."""
        content = b'x' * (10 * 1024 * 1024)  # Exactly 10MB
        file = SimpleUploadedFile('exact.txt', content, content_type='text/plain')
        serializer = FileUploadSerializer(data={'file': file})
        assert serializer.is_valid(), serializer.errors

    def test_missing_file_rejected(self):
        """Test missing file is rejected."""
        serializer = FileUploadSerializer(data={})
        assert not serializer.is_valid()
        assert 'file' in serializer.errors