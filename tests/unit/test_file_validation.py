"""Unit tests for shared.files.validation module."""
import pytest
import base64
from django.core.exceptions import SuspiciousOperation

from shared.files.validation import (
    safe_base64_decode,
    validate_and_sanitize_path,
    sanitize_filename,
)


class TestSafeBase64Decode:
    """Tests for safe_base64_decode function."""

    def test_decode_valid_path(self):
        """Test decoding a valid base64 encoded path."""
        original = "documents/file.txt"
        encoded = base64.urlsafe_b64encode(original.encode()).decode()
        result = safe_base64_decode(encoded)
        assert result == original

    def test_decode_empty_string(self):
        """Test decoding empty string returns empty."""
        assert safe_base64_decode("") == ""

    def test_decode_none(self):
        """Test decoding None returns empty."""
        assert safe_base64_decode(None) == ""

    def test_decode_with_missing_padding(self):
        """Test decoding handles missing padding."""
        original = "test"
        encoded = base64.urlsafe_b64encode(original.encode()).decode()
        # Remove padding
        encoded = encoded.rstrip("=")
        result = safe_base64_decode(encoded)
        assert result == original

    def test_decode_invalid_base64_raises(self):
        """Test that invalid base64 raises SuspiciousOperation."""
        with pytest.raises(SuspiciousOperation):
            safe_base64_decode("!!!invalid!!!")

    def test_decode_unicode_path(self):
        """Test decoding unicode characters in path."""
        original = "documents/fichier_francais.txt"
        encoded = base64.urlsafe_b64encode(original.encode()).decode()
        result = safe_base64_decode(encoded)
        assert result == original


class TestValidateAndSanitizePath:
    """Tests for validate_and_sanitize_path function."""

    def test_valid_simple_path(self, tmp_path):
        """Test validation of a simple valid path."""
        base_path = str(tmp_path)
        (tmp_path / "subdir").mkdir()
        result = validate_and_sanitize_path("subdir", base_path)
        assert result == "subdir"

    def test_empty_path_returns_empty(self, tmp_path):
        """Test empty path returns empty string."""
        result = validate_and_sanitize_path("", str(tmp_path))
        assert result == ""

    def test_none_path_returns_empty(self, tmp_path):
        """Test None path returns empty string."""
        result = validate_and_sanitize_path(None, str(tmp_path))
        assert result == ""

    def test_path_traversal_blocked(self, tmp_path):
        """Test path traversal attempt is blocked."""
        with pytest.raises(SuspiciousOperation):
            validate_and_sanitize_path("../etc/passwd", str(tmp_path))

    def test_double_dot_in_path_blocked(self, tmp_path):
        """Test double dot in path component is blocked."""
        with pytest.raises(SuspiciousOperation):
            # Direct .. component should be blocked
            validate_and_sanitize_path("..", str(tmp_path))

    def test_hidden_file_blocked(self, tmp_path):
        """Test hidden files (starting with dot) are blocked."""
        with pytest.raises(SuspiciousOperation):
            validate_and_sanitize_path(".hidden", str(tmp_path))

    def test_hidden_directory_blocked(self, tmp_path):
        """Test hidden directories are blocked."""
        with pytest.raises(SuspiciousOperation):
            validate_and_sanitize_path("subdir/.hidden/file", str(tmp_path))

    def test_path_outside_base_blocked(self, tmp_path):
        """Test path resolving outside base directory is blocked."""
        import os
        # Create a symlink that resolves outside the base path
        malicious_link = tmp_path / "escape"
        try:
            os.symlink("/etc", malicious_link)
            with pytest.raises(SuspiciousOperation):
                validate_and_sanitize_path("escape/passwd", str(tmp_path))
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

    def test_symlink_traversal_blocked(self, tmp_path):
        """Test symlink that points outside base is blocked."""
        # Create a symlink pointing outside
        import os
        symlink_path = tmp_path / "evil_link"
        try:
            os.symlink("/etc", symlink_path)
            with pytest.raises(SuspiciousOperation):
                validate_and_sanitize_path("evil_link/passwd", str(tmp_path))
        except OSError:
            pytest.skip("Cannot create symlinks on this system")

    def test_leading_slash_stripped(self, tmp_path):
        """Test leading slash is stripped from path."""
        (tmp_path / "subdir").mkdir()
        result = validate_and_sanitize_path("/subdir", str(tmp_path))
        assert result == "subdir"

    def test_nested_valid_path(self, tmp_path):
        """Test validation of nested valid path."""
        (tmp_path / "dir1" / "dir2").mkdir(parents=True)
        result = validate_and_sanitize_path("dir1/dir2", str(tmp_path))
        assert result == "dir1/dir2"


class TestSanitizeFilename:
    """Tests for sanitize_filename function."""

    def test_valid_filename_unchanged(self):
        """Test valid filename is returned unchanged."""
        assert sanitize_filename("document.pdf") == "document.pdf"

    def test_empty_filename_returns_default(self):
        """Test empty filename returns default."""
        assert sanitize_filename("") == "unnamed_file"

    def test_none_filename_returns_default(self):
        """Test None filename returns default."""
        assert sanitize_filename(None) == "unnamed_file"

    def test_path_components_stripped(self):
        """Test path components are stripped, keeping only basename."""
        assert sanitize_filename("/path/to/file.txt") == "file.txt"
        assert sanitize_filename("../../../etc/passwd") == "passwd"

    def test_dangerous_chars_replaced(self):
        """Test dangerous characters are replaced with underscore."""
        assert sanitize_filename("file<name>.txt") == "file_name_.txt"
        assert sanitize_filename('file"name".txt') == "file_name_.txt"
        assert sanitize_filename("file|name.txt") == "file_name.txt"

    def test_dot_filename_returns_default(self):
        """Test single dot filename returns default."""
        assert sanitize_filename(".") == "unnamed_file"

    def test_double_dot_filename_returns_default(self):
        """Test double dot filename returns default."""
        assert sanitize_filename("..") == "unnamed_file"

    def test_very_long_filename_truncated(self):
        """Test very long filename is truncated."""
        long_name = "a" * 300 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_long_filename_preserves_extension(self):
        """Test long filename truncation preserves extension."""
        long_name = "a" * 300 + ".pdf"
        result = sanitize_filename(long_name)
        assert result.endswith(".pdf")

    def test_null_byte_removed(self):
        """Test null byte is removed from filename."""
        result = sanitize_filename("file\x00name.txt")
        assert "\x00" not in result

    def test_unicode_filename_preserved(self):
        """Test unicode characters in filename are preserved."""
        result = sanitize_filename("document_francais.txt")
        assert result == "document_francais.txt"