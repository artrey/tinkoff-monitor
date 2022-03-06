import logging

from django.db.models import Case, Count, IntegerField, When

from apps.tasks.bot import send_atm_info
from apps.tasks.processing import get_info
from tinkoff.celery import app

logger = logging.getLogger(__name__)


@app.task(autoretry_for=(Exception,), max_retries=3, default_retry_delay=2)
def grab_info(atm_id: int):
    from apps.monitor.models import ATM

    atm = ATM.objects.get(id=atm_id)
    info = get_info(atm.lat, atm.lon)
    if not info:
        logger.warning("error while getting info")
        return

    if info.rub != atm.last_info.rub or info.usd != atm.last_info.usd or info.eur != atm.last_info.eur:
        atm.update_currencies(rub=info.rub, usd=info.usd, eur=info.eur)
        send_atm_info(atm.id)
    else:
        atm.last_info.save(update_fields=["updated_at"])


@app.task
def grab_actual_atms():
    from apps.monitor.models import ATM

    atm_ids = (
        ATM.objects.annotate(
            subscribers_count=Count(
                Case(
                    When(subscribers__has_subscription=True, then=1),
                    output_field=IntegerField(),
                )
            )
        )
        .filter(subscribers_count__gt=0)
        .order_by("subscribers_count")
        .values_list("id", flat=True)
    )
    for atm_id in atm_ids:
        grab_info(atm_id)


@app.task
def infinite_grab_actual_atms():
    grab_actual_atms()
    infinite_grab_actual_atms.delay()
