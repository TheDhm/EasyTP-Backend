from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import App, AccessGroup


class Command(BaseCommand):
    help = 'Create LOGISIM app and Guest group with access'

    def handle(self, *args, **options):
        try:
            with transaction.atomic():
                # Create or get the Guest group
                guest_group, created = AccessGroup.objects.get_or_create(
                    name='Guest',
                    defaults={'name': 'Guest'}
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS('Successfully created Guest group')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('Guest group already exists')
                    )

                # Create or get the LOGISIM app
                logisim_app, created = App.objects.get_or_create(
                    name='LOGISIM',
                    defaults={
                        'name': 'LOGISIM',
                        'image': 'logisim:latest' 
                    }
                )
                
                if created:
                    self.stdout.write(
                        self.style.SUCCESS('Successfully created LOGISIM app')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING('LOGISIM app already exists')
                    )

                # Give Guest group access to LOGISIM app
                logisim_app.group.add(guest_group)
                
                self.stdout.write(
                    self.style.SUCCESS('Successfully gave Guest group access to LOGISIM app')
                )

                # Display current status
                self.stdout.write('\n--- Current Status ---')
                self.stdout.write(f'Guest group has access to: {guest_group.has_access_to()}')
                self.stdout.write(f'LOGISIM app is accessible by: {logisim_app.groups()}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error occurred: {str(e)}')
            )
            raise