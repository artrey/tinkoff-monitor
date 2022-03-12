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


@app.task(autoretry_for=(Exception,), max_retries=3, default_retry_delay=10)
def send_atm_info(atm_id: int, changed_rub: bool, changed_usd: bool, changed_eur: bool):
    from apps.monitor.models import ATM

    atm = ATM.objects.select_related("last_info").get(id=atm_id)

    info = atm.notify_settings.filter(user__has_subscription=True).values_list(
        "user_id",
        "need_rub",
        "need_usd",
        "need_eur",
    )
    if not info:
        return

    message = atm.info_message_markdown

    for tid, need_rub, need_usd, need_eur in info:
        if need_rub and changed_rub or need_usd and changed_usd or need_eur and changed_eur:
            send_message(message, tid, parse_mode="markdown", disable_web_page_preview=True)
