"""File operation utilities for reading and writing files securely."""

import base64
import os

from django.utils.html import escape


def get_sub_files_secure(user_path, path, return_format="tuple"):
    """
    Securely get directory contents with size information.

    Args:
        user_path: The base user directory path
        path: The relative path within user_path
        return_format: 'tuple' returns (files, directories) lists,
                       'dict' returns a dict keyed by filename (legacy format)

    Returns:
        If return_format='tuple': (files_list, directories_list)
        If return_format='dict': {filename: {path, is_dir, size, escaped_name}}
    """
    files = []
    directories = []
    sub_files_dict = {}

    try:
        full_path = os.path.join(user_path, path) if path else user_path

        if not os.path.exists(full_path) or not os.path.isdir(full_path):
            if return_format == "dict":
                return sub_files_dict
            return files, directories

        for item in os.listdir(full_path):
            # Skip hidden files and dangerous names
            if item.startswith(".") or item in ["..", "."]:
                continue

            item_path = os.path.join(full_path, item)

            # Skip symlinks for security
            if os.path.islink(item_path):
                continue

            try:
                relative_path = os.path.join(path, item) if path else item
                encoded_path = base64.urlsafe_b64encode(relative_path.encode("utf-8")).decode()

                item_data = {
                    "name": item,
                    "path": encoded_path,
                    "is_dir": os.path.isdir(item_path),
                    "size": None,
                    "escaped_name": escape(item),
                }

                if os.path.isdir(item_path):
                    directories.append(item_data)
                    sub_files_dict[item] = {
                        "path": encoded_path,
                        "is_dir": True,
                        "size": None,
                        "escaped_name": escape(item),
                    }
                elif os.path.isfile(item_path):
                    try:
                        file_size = os.path.getsize(item_path)
                        item_data["size"] = file_size
                        files.append(item_data)
                        sub_files_dict[item] = {
                            "path": encoded_path,
                            "is_dir": False,
                            "size": file_size,
                            "escaped_name": escape(item),
                        }
                    except OSError:
                        # Skip files we can't access
                        continue
            except (UnicodeEncodeError, OSError):
                # Skip problematic files
                continue

    except (OSError, IOError):
        pass  # Return empty result if directory can't be accessed

    if return_format == "dict":
        return sub_files_dict
    return files, directories


def save_file_secure(file_path, uploaded_file):
    """Securely save uploaded file."""
    # Ensure directory exists
    directory = os.path.dirname(file_path)
    os.makedirs(directory, exist_ok=True)

    # Write file in chunks to handle large files efficiently and securely
    with open(file_path, "wb") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    # Set restrictive permissions (owner read/write only)
    os.chmod(file_path, 0o600)
