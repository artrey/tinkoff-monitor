from django.core.management.base import BaseCommand

from apps.tasks.monitor import infinite_grab_actual_atms


class Command(BaseCommand):
    help = "Infinite grabbing"

    def handle(self, *args, **options):
        infinite_grab_actual_atms.delay()
