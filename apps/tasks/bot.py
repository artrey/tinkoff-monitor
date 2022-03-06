import logging
from functools import lru_cache

import telegram
from django.conf import settings

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


def money2str(value: int) -> str:
    if value >= 1000:
        return f"{value // 1000} {value % 1000:03}"
    return str(value)


def message_threshold(value: int, threshold: int) -> str:
    if value >= threshold:
        return f"более {money2str(threshold)}"
    return money2str(value)


@app.task(autoretry_for=(Exception,), max_retries=3, default_retry_delay=10)
def send_atm_info(atm_id: int):
    from apps.monitor.models import ATM

    atm = ATM.objects.get(id=atm_id)

    ids = atm.subscribers.filter(has_subscription=True).values_list("id", flat=True)
    if not ids:
        return

    message = f"""
*{atm.address}*

*RUB:* {message_threshold(atm.last_info.rub, 300000)} ₽
*USD:* {message_threshold(atm.last_info.usd, 5000)} $
*EUR:* {message_threshold(atm.last_info.eur, 5000)} €
    """

    for tid in ids:
        send_message(message, tid, parse_mode="markdown")