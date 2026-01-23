# signals.py
import logging
import os
import shutil

from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_out
from django.db.models.signals import post_delete
from django.dispatch import receiver

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(user_logged_out)
def delete_guest_user(sender, request, user, **kwargs):
    if user.is_guest():
        user.delete()


@receiver(post_delete, sender=User)
def delete_user_folder(sender, instance, **kwargs):
    """Delete the user's directory when the user is deleted."""
    user_folder = os.path.join("/USERDATA", instance.username)
    logger.info(f"delete_user_folder triggered for user: {instance.username}")
    logger.info(f"Checking folder: {user_folder}")

    if os.path.exists(user_folder):
        logger.info(f"Folder exists, attempting to delete: {user_folder}")
        try:
            shutil.rmtree(user_folder)
            logger.info(f"Successfully deleted folder: {user_folder}")
        except OSError as e:
            logger.error(f"Failed to delete folder {user_folder}: {e}", exc_info=True)
    else:
        logger.warning(f"Folder does not exist: {user_folder}")
