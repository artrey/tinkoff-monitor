import logging
from functools import lru_cache

import telegram
from django.conf import settings

from apps.monitor.models import ATM
from tinkoff.celery import app

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def get_bot() -> telegram.Bot:
    return telegram.Bot(token=settings.TELEGRAM_BOT_TOKEN)


@app.task(autoretry_for=(Exception,), max_retries=3, default_retry_delay=10)
def send_message(text: str, telegram_user_id: str, *args, **kwargs):
    try:
        get_bot().send_message(telegram_user_id, text, *args, **kwargs)
    except telegram.error.Unauthorized:
        logger.warning(f"Telegram user {telegram_user_id} blocked the bot")


@app.task(autoretry_for=(Exception,), max_retries=3, default_retry_delay=10)
def send_atm_info(atm_id: int):
    atm = ATM.objects.get(id=atm_id)

    ids = atm.subscribers.values_list("id", flat=True)
    if not ids:
        return

    # TODO
    message = str(atm.last_info.usd)

    for tid in ids:
        send_message(message, tid, parse_mode="markdown")
