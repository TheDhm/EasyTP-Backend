"""Storage calculation utilities."""

import os


def get_actual_storage_usage(user_path):
    """Calculate actual storage usage by scanning filesystem.

    Args:
        user_path: The path to scan for storage usage

    Returns:
        float: Storage usage in MB
    """
    total_size = 0
    try:
        for root, dirs, files in os.walk(user_path):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    # Only count regular files, not symlinks
                    if os.path.isfile(file_path) and not os.path.islink(file_path):
                        total_size += os.path.getsize(file_path)
                except (OSError, IOError):
                    continue  # Skip files we can't access
    except (OSError, IOError):
        pass

    return total_size / (1024 * 1024)  # Convert to MB
