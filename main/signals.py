# signals.py
import os
import shutil

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_delete
from django.dispatch import receiver

User = get_user_model()


@receiver(user_logged_out)
def delete_guest_user(sender, request, user, **kwargs):
    if user.is_guest():
        user.delete()  # Delete guest account after logout


@receiver(post_delete, sender=User)
def delete_user_folder(sender, instance, **kwargs):
    """
    Deletes the user's directory when the user is deleted.
    """

    user_folder = os.path.join("/USERDATA", instance.username)

    if os.path.exists(user_folder):
        try:
            shutil.rmtree(user_folder)  # Recursively delete directory
        except OSError as e:
            print(f"Error deleting user folder: {e}")  # Log errors (or use Django logging)
