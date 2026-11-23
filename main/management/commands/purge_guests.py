from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from main.models import DefaultUser


class Command(BaseCommand):
    help = "Delete guest accounts older than --hours (their folders go with them)."

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=24)

    def handle(self, *args, hours, **options):
        cutoff = timezone.now() - timedelta(hours=hours)
        guests = DefaultUser.objects.filter(role=DefaultUser.GUEST, date_joined__lt=cutoff)
        count = guests.count()
        # Per-instance delete so the post_delete signal removes each /USERDATA folder.
        for guest in guests:
            guest.delete()
        self.stdout.write(f"Deleted {count} guest account(s)")
