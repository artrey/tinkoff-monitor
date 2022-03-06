from django.core.management.base import BaseCommand

from apps.tgbot.bot import configure_bot


class Command(BaseCommand):
    help = "Start bot"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Setup bot"))
        updater = configure_bot()
        self.stdout.write(self.style.SUCCESS("Start polling..."))
        updater.start_polling()
