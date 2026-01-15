"""File path validation and sanitization utilities."""

import base64
import binascii
import os

from django.core.exceptions import SuspiciousOperation


def sanitize_filename(filename):
    """Sanitize filename to prevent path traversal and other attacks."""
    if not filename:
        return "unnamed_file"

    # Use only the basename to strip any path components
    clean_name = os.path.basename(filename)

    # Remove or replace dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "|", "?", "*", "\0"]
    for char in dangerous_chars:
        clean_name = clean_name.replace(char, "_")

    # Ensure filename isn't empty after cleaning
    if not clean_name or clean_name in [".", ".."]:
        clean_name = "unnamed_file"

    # Limit filename length
    if len(clean_name) > 255:
        name, ext = os.path.splitext(clean_name)
        clean_name = name[:250] + ext

    return clean_name


def safe_base64_decode(encoded_path):
    """Safely decode base64 with proper padding and error handling."""
    if not encoded_path:
        return ""

    try:
        # Add padding if necessary
        pad = len(encoded_path) % 4
        if pad:
            encoded_path += "=" * (4 - pad)

        decoded = base64.urlsafe_b64decode(encoded_path).decode("utf-8")
        return decoded
    except (binascii.Error, UnicodeDecodeError, ValueError):
        raise SuspiciousOperation("Invalid path encoding")


def validate_and_sanitize_path(path, user_base_path):
    """Comprehensive path validation and sanitization."""
    if not path:
        return ""

    # Normalize the path
    path = os.path.normpath(path)

    # Remove leading slash and strip whitespace
    path = path.lstrip("/").strip()

    # Block dangerous path components
    path_parts = path.split("/")
    for part in path_parts:
        if part in [".", "..", ""] or part.startswith("."):
            raise SuspiciousOperation("Invalid path component")

    # Construct full path and resolve symlinks
    if path:
        full_path = os.path.join(user_base_path, path)
    else:
        full_path = user_base_path

    real_path = os.path.realpath(full_path)
    real_base = os.path.realpath(user_base_path)

    # Ensure path is within allowed directory
    if not real_path.startswith(real_base + os.sep) and real_path != real_base:
        raise SuspiciousOperation("Path outside allowed directory")

    return path
