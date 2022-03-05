from dataclasses import asdict

from django.utils import timezone

from apps.monitor.models import ATM, ATMHistoryInfo, ATMLastInfo
from apps.tasks.bot import send_atm_info
from apps.tasks.processing import get_info
from tinkoff.celery import app


@app.task(autoretry_for=(Exception,), max_retries=3, default_retry_delay=2)
def grab_info(atm_id: int):
    atm = ATM.objects.get(id=atm_id)
    info = get_info(atm.lat, atm.lon)
    if info.rub != atm.last_info.rub or info.usd != atm.last_info.usd or info.eur != atm.last_info.eur:
        ATMLastInfo.objects.filter(atm_id=atm_id).update(**asdict(info), updated_at=timezone.now())
        ATMHistoryInfo.objects.create(atm_id=atm_id, **asdict(info))
        send_atm_info(atm.id)
