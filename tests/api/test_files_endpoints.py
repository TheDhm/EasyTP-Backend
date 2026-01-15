"""API tests for file endpoints using temp directories."""
import pytest
import base64
import os
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient


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
def student_file_dir(tmp_path, student_user):
    """Create a temp directory for student files."""
    user_dir = tmp_path / "userdata" / student_user.username
    user_dir.mkdir(parents=True)
    return str(user_dir) + "/"


@pytest.fixture
def readonly_dir(tmp_path):
    """Create a temp directory for readonly files."""
    readonly = tmp_path / "readonly"
    readonly.mkdir(parents=True)
    return str(readonly) + "/"


def encode_path(path):
    """Base64 encode a path for URL."""
    return base64.urlsafe_b64encode(path.encode('utf-8')).decode()


def get_user_path_for_role(user, student_dir, readonly_dir):
    """Helper to determine which path a user should use based on role."""
    from main.models import DefaultUser
    if user.role in [DefaultUser.TEACHER, DefaultUser.ADMIN] or user.is_superuser:
        return readonly_dir
    return student_dir


class TestFileExplorerViewGET:
    """Tests for GET /files/ endpoint (list files)."""

    def test_unauthenticated_access_denied(self, api_client):
        """Test unauthenticated access is denied."""
        response = api_client.get('/files/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_can_list_files(self, authenticated_student_client, student_user, student_file_dir):
        """Test student can list files in their directory."""
        # Create test file
        test_file = os.path.join(student_file_dir, 'testfile.txt')
        with open(test_file, 'w') as f:
            f.write('test content')

        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)

            response = authenticated_student_client.get('/files/')

            assert response.status_code == status.HTTP_200_OK
            assert 'files' in response.data
            assert 'directories' in response.data
            assert 'current_path' in response.data

    def test_student_has_storage_usage(self, authenticated_student_client, student_user, student_file_dir):
        """Test student sees storage usage."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)
            with patch('api.views.get_actual_storage_usage', return_value=5.0):
                response = authenticated_student_client.get('/files/')

                assert response.status_code == status.HTTP_200_OK
                assert response.data['storage_usage'] is not None
                assert 'current_mb' in response.data['storage_usage']

    def test_teacher_can_list_files(self, authenticated_teacher_client, readonly_dir):
        """Test teacher can list files in READONLY directory."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (readonly_dir, False)

            response = authenticated_teacher_client.get('/files/')

            assert response.status_code == status.HTTP_200_OK
            # Teachers don't have storage limits
            assert response.data['storage_usage'] is None

    def test_navigate_to_subdirectory(self, authenticated_student_client, student_user, student_file_dir):
        """Test navigation to subdirectory via path parameter."""
        subdir = os.path.join(student_file_dir, 'subdir')
        os.makedirs(subdir, exist_ok=True)

        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)

            encoded_path = encode_path('subdir')
            response = authenticated_student_client.get(f'/files/{encoded_path}/')

            assert response.status_code == status.HTTP_200_OK
            assert response.data['current_path'] == '/subdir'


class TestFileExplorerViewPOST:
    """Tests for POST /files/ endpoint (upload files)."""

    def test_unauthenticated_upload_denied(self, api_client):
        """Test unauthenticated upload is denied."""
        test_file = SimpleUploadedFile('test.txt', b'test content', content_type='text/plain')
        response = api_client.post('/files/', {'file': test_file}, format='multipart')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_can_upload_file(self, authenticated_student_client, student_user, student_file_dir):
        """Test student can upload a file."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)
            with patch('api.views.get_actual_storage_usage', return_value=0.0):
                test_file = SimpleUploadedFile('upload_test.txt', b'test content', content_type='text/plain')
                response = authenticated_student_client.post('/files/', {'file': test_file}, format='multipart')

                assert response.status_code == status.HTTP_201_CREATED
                assert 'filename' in response.data
                assert 'size_mb' in response.data

                # Verify file was created
                uploaded_path = os.path.join(student_file_dir, response.data['filename'])
                assert os.path.exists(uploaded_path)

    def test_upload_to_subdirectory(self, authenticated_student_client, student_user, student_file_dir):
        """Test uploading to a subdirectory."""
        subdir = os.path.join(student_file_dir, 'uploads')
        os.makedirs(subdir, exist_ok=True)

        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)
            with patch('api.views.get_actual_storage_usage', return_value=0.0):
                encoded_path = encode_path('uploads')
                test_file = SimpleUploadedFile('subdir_upload.txt', b'subdir content', content_type='text/plain')
                response = authenticated_student_client.post(f'/files/{encoded_path}/', {'file': test_file}, format='multipart')

                assert response.status_code == status.HTTP_201_CREATED

    def test_file_size_limit_enforced(self, authenticated_student_client, student_user, student_file_dir):
        """Test 10MB file size limit is enforced."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)

            # Create file larger than 10MB
            large_content = b'x' * (11 * 1024 * 1024)  # 11MB
            test_file = SimpleUploadedFile('large_file.txt', large_content, content_type='text/plain')
            response = authenticated_student_client.post('/files/', {'file': test_file}, format='multipart')

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert 'file' in response.data

    def test_storage_quota_enforced(self, authenticated_student_client, student_user, student_file_dir):
        """Test storage quota is enforced for students."""
        # Set user's upload limit very low
        student_user.upload_limit = 0.001  # 1KB limit
        student_user.save()

        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)
            with patch('api.views.get_actual_storage_usage', return_value=0.0):
                test_file = SimpleUploadedFile('quota_test.txt', b'x' * 2048, content_type='text/plain')
                response = authenticated_student_client.post('/files/', {'file': test_file}, format='multipart')

                assert response.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE

    def test_duplicate_file_renamed(self, authenticated_student_client, student_user, student_file_dir):
        """Test duplicate files are auto-renamed."""
        # Create first file
        existing_file = os.path.join(student_file_dir, 'duplicate.txt')
        with open(existing_file, 'w') as f:
            f.write('existing')

        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)
            with patch('api.views.get_actual_storage_usage', return_value=0.0):
                test_file = SimpleUploadedFile('duplicate.txt', b'new content', content_type='text/plain')
                response = authenticated_student_client.post('/files/', {'file': test_file}, format='multipart')

                assert response.status_code == status.HTTP_201_CREATED
                assert response.data['filename'] != 'duplicate.txt'
                assert 'duplicate_' in response.data['filename']

    def test_no_file_provided_error(self, authenticated_student_client, student_file_dir):
        """Test error when no file is provided."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)

            response = authenticated_student_client.post('/files/', {}, format='multipart')
            assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestFileExplorerViewDELETE:
    """Tests for DELETE /files/ endpoint (delete files)."""

    def test_unauthenticated_delete_denied(self, api_client):
        """Test unauthenticated delete is denied."""
        encoded_path = encode_path('test.txt')
        response = api_client.delete(f'/files/{encoded_path}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_can_delete_file(self, authenticated_student_client, student_user, student_file_dir):
        """Test student can delete their own file."""
        # Create file to delete
        test_file_path = os.path.join(student_file_dir, 'to_delete.txt')
        with open(test_file_path, 'w') as f:
            f.write('delete me')

        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)
            with patch('api.views.get_actual_storage_usage', return_value=0.0):
                encoded_path = encode_path('to_delete.txt')
                response = authenticated_student_client.delete(f'/files/{encoded_path}/')

                assert response.status_code == status.HTTP_200_OK
                assert response.data['filename'] == 'to_delete.txt'
                assert 'size_mb_freed' in response.data
                assert not os.path.exists(test_file_path)

    def test_delete_nonexistent_file_error(self, authenticated_student_client, student_file_dir):
        """Test deleting nonexistent file returns error."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)

            encoded_path = encode_path('nonexistent.txt')
            response = authenticated_student_client.delete(f'/files/{encoded_path}/')

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_directory_blocked(self, authenticated_student_client, student_file_dir):
        """Test deleting directories is blocked."""
        subdir = os.path.join(student_file_dir, 'no_delete_dir')
        os.makedirs(subdir, exist_ok=True)

        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (student_file_dir, False)

            encoded_path = encode_path('no_delete_dir')
            response = authenticated_student_client.delete(f'/files/{encoded_path}/')

            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert os.path.exists(subdir)


class TestDownloadFileView:
    """Tests for GET /download/ endpoint."""

    def test_unauthenticated_download_denied(self, api_client):
        """Test unauthenticated download is denied."""
        encoded_path = encode_path('test.txt')
        response = api_client.get(f'/download/{encoded_path}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_can_download_file(self, authenticated_student_client, student_user, student_file_dir):
        """Test student can download their own file."""
        # Create file to download
        test_file_path = os.path.join(student_file_dir, 'download_me.txt')
        with open(test_file_path, 'w') as f:
            f.write('downloadable content')

        with patch('api.views.DownloadFileView._get_user_path') as mock_path:
            mock_path.return_value = student_file_dir

            encoded_path = encode_path('download_me.txt')
            response = authenticated_student_client.get(f'/download/{encoded_path}/')

            assert response.status_code == status.HTTP_200_OK
            assert response.get('Content-Disposition') is not None
            assert 'attachment' in response.get('Content-Disposition')

    def test_download_nonexistent_file_error(self, authenticated_student_client, student_file_dir):
        """Test downloading nonexistent file returns 404."""
        with patch('api.views.DownloadFileView._get_user_path') as mock_path:
            mock_path.return_value = student_file_dir

            encoded_path = encode_path('nonexistent.txt')
            response = authenticated_student_client.get(f'/download/{encoded_path}/')

            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_download_directory_blocked(self, authenticated_student_client, student_file_dir):
        """Test downloading directory is blocked."""
        subdir = os.path.join(student_file_dir, 'no_download_dir')
        os.makedirs(subdir, exist_ok=True)

        with patch('api.views.DownloadFileView._get_user_path') as mock_path:
            mock_path.return_value = student_file_dir

            encoded_path = encode_path('no_download_dir')
            response = authenticated_student_client.get(f'/download/{encoded_path}/')

            assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTeacherFileAccess:
    """Tests for teacher/admin file access patterns."""

    def test_teacher_uses_readonly_directory(self, authenticated_teacher_client, readonly_dir):
        """Test teacher uses readonly directory."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (readonly_dir, False)

            response = authenticated_teacher_client.get('/files/')

            assert response.status_code == status.HTTP_200_OK
            assert response.data['storage_usage'] is None

    def test_admin_uses_readonly_directory(self, authenticated_admin_client, readonly_dir):
        """Test admin uses readonly directory."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (readonly_dir, False)

            response = authenticated_admin_client.get('/files/')

            assert response.status_code == status.HTTP_200_OK
            assert response.data['storage_usage'] is None

    def test_teacher_can_upload(self, authenticated_teacher_client, readonly_dir):
        """Test teacher can upload to readonly."""
        with patch('api.views.FileExplorerView._get_user_path') as mock_path:
            mock_path.return_value = (readonly_dir, False)

            test_file = SimpleUploadedFile('teacher_upload.txt', b'teacher content', content_type='text/plain')
            response = authenticated_teacher_client.post('/files/', {'file': test_file}, format='multipart')

            assert response.status_code == status.HTTP_201_CREATED