import decimal
import json
from argparse import ArgumentParser

from django.core.management.base import BaseCommand

from apps.monitor.models import ATM
from apps.tasks.processing import get_info


# coordinates source: https://moskva.1000bankov.ru/bankomats/2673/
class Command(BaseCommand):
    help = "Create atms from file with coordinates"

    def add_arguments(self, parser: ArgumentParser):
        parser.add_argument("input", help="JSON with coordinates of ATMs")

    def handle(self, *args, **options):
        with open(options["input"], "r") as fd:
            data = json.load(fd)

        for atm_info in data:
            lat, lon = map(decimal.Decimal, atm_info["coords"])

            if ATM.objects.filter(lat=lat, lon=lon).exists():
                continue

            info = get_info(lat, lon)
            if info:
                atm = ATM.objects.create(address=info.address, worktime=info.worktime, lon=lon, lat=lat)
                atm.update_currencies(rub=info.rub, usd=info.usd, eur=info.eur)
                self.stdout.write(self.style.SUCCESS(info.address))
            else:
                self.stderr.write(f"{atm_info['coords']} | {atm_info['clusterCaption']}")
