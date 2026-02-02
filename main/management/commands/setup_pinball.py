from django.core.management.base import BaseCommand
from django.db import transaction

from main.models import AccessGroup, App


class Command(BaseCommand):
    help = "Create PINBALL app and Guest group with access"

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Create or get the Guest group
                guest_group, created = AccessGroup.objects.get_or_create(
                    name="Guest", defaults={"name": "Guest"}
                )

                if created:
                    self.stdout.write(self.style.SUCCESS("Successfully created Guest group"))
                else:
                    self.stdout.write(self.style.WARNING("Guest group already exists"))

                # Create or get the PINBALL app
                pinball_app, created = App.objects.get_or_create(
                    name="PINBALL", defaults={"name": "PINBALL", "image": "pinball:latest"}
                )

                if created:
                    self.stdout.write(self.style.SUCCESS("Successfully created PINBALL app"))
                else:
                    self.stdout.write(self.style.WARNING("PINBALL app already exists"))

                # Give Guest group access to PINBALL app
                pinball_app.group.add(guest_group)

                self.stdout.write(
                    self.style.SUCCESS("Successfully gave Guest group access to PINBALL app")
                )

                # Display current status
                self.stdout.write("\n--- Current Status ---")
                self.stdout.write(f"Guest group has access to: {guest_group.has_access_to()}")
                self.stdout.write(f"PINBALL app is accessible by: {pinball_app.groups()}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error occurred: {str(e)}"))
            raise
