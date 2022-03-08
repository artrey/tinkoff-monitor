import decimal
import functools
import logging

from django.conf import settings
from django.db.models import F
from django.db.models.functions import Cos, Power, Sqrt
from django.urls import reverse
from telegram import KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext, CommandHandler, ConversationHandler, Filters, MessageHandler, Updater

from apps.monitor.models import ATM
from apps.tgbot.models import NotifySettings, TelegramUser

logger = logging.getLogger(__name__)


def inject_user(func: callable):
    @functools.wraps(func)
    def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        user = TelegramUser.objects.filter(id=update.effective_message.chat_id).first()
        if not user:
            update.effective_message.reply_text(
                text="Что-то пошло не так... Попробуйте выполнить команду /start",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            return func(update, context, *args, **kwargs, user=user)

    return wrapper


def start_command(update: Update, context: CallbackContext):
    data = update.effective_message.from_user.to_dict()
    TelegramUser.objects.update_or_create(id=data.pop("id"), defaults=dict(extra_data=data))
    help_command(update, context)


def help_command(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        "Привет! Я возьму на себя работу по слежению за деньгами в банкоматах 🤝\n\n"
        "Ты выбираешь банкоматы, до которых можешь быстро добраться, а я первым сообщу тебе"
        " когда в них появятся деньги. Выбирай банкоматы поближе,"
        " иначе можно не успеть забрать валюту 😱"
        # "\n\nЗа свои услуги я возьму с тебя 100 рублей. Плати один раз - пользуйся всегда 😉"
    )


@inject_user
def payment_handler(update: Update, context: CallbackContext, user: TelegramUser):
    if user.has_subscription:
        update.effective_message.reply_text(
            text="Все в порядке, подписка активна, платить больше не нужно. Спасибо за доверие 👍",
            reply_markup=ReplyKeyboardRemove(),
        )
    else:
        payment_link = settings.APP_BASE_URL + reverse("payment", kwargs=dict(tuid=user.id))
        update.effective_message.reply_text(
            text=f"Ссылка на оплату:\n{payment_link}\n\nПосле оплаты я начну следить за деньгами для тебя 😉",
            reply_markup=ReplyKeyboardRemove(),
        )


def fallback_exit_handler(update: Update, context: CallbackContext):
    update.effective_message.reply_text(text="Что-то не получилось... Попробуйте повторить с начала")
    return ConversationHandler.END


CURRENCY_SAVE = range(1)


@inject_user
def currency_handler(update: Update, context: CallbackContext, user: TelegramUser):
    if not user.notify_settings.exists():
        update.effective_message.reply_text(text="Сначала надо настроить мониторинг")
        return ConversationHandler.END

    choices = ReplyKeyboardMarkup(
        [
            ["рубли ₽", "доллары $", "евро €"],
            ["доллары и евро $/€", "все ₽/$/€"],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    update.effective_message.reply_text(
        text="Какая валюта интересует?",
        reply_markup=choices,
    )
    return CURRENCY_SAVE


@inject_user
def currency_finish_handler(update: Update, context: CallbackContext, user: TelegramUser):
    need_rub = "₽" in update.effective_message.text
    need_usd = "$" in update.effective_message.text
    need_eur = "€" in update.effective_message.text
    user.notify_settings.all().update(need_rub=need_rub, need_usd=need_usd, need_eur=need_eur)
    update.effective_message.reply_text(text="Отлично! Запомнил 😉", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


SCAN_REQUEST_POS, SCAN_REQUEST_RADIUS = range(2)


def scan_handler(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        text="Укажите локацию с помощью кнопки ниже или введите координаты в виде:"
        "\n\nширота, долгота\n\nразделитель дробной части в координатах - точка",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Мое местоположение", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return SCAN_REQUEST_POS


def set_atms(user: TelegramUser, lon: float, lat: float, radius: float) -> int:
    ns = user.notify_settings.first()
    need_rub, need_usd, need_eur = True, True, True
    if ns:
        need_rub, need_usd, need_eur = ns.need_rub, ns.need_usd, ns.need_eur

    lon = decimal.Decimal(lon)
    lat = decimal.Decimal(lat)
    # https://stackoverflow.com/questions/61135374/postgresql-calculate-distance-between-two-points-without-using-postgis
    atm_ids = (
        ATM.objects.annotate(
            distance=Sqrt(
                Power(decimal.Decimal(69.1) * (F("lon") - lon) * Cos(lat / decimal.Decimal(57.3)), 2)
                + Power(decimal.Decimal(69.1) * (F("lat") - lat), 2)
            )
        )
        .filter(distance__lte=radius)
        .values_list("id", flat=True)
    )

    user.notify_settings.all().delete()
    NotifySettings.objects.bulk_create(
        [
            NotifySettings(user=user, atm_id=atm_id, need_rub=need_rub, need_usd=need_usd, need_eur=need_eur)
            for atm_id in atm_ids
        ],
        ignore_conflicts=True,
    )
    return len(atm_ids)


def request_radius(update: Update, context: CallbackContext):
    update.effective_message.reply_text(text="Укажите радиус поиска, в километрах\n\nразделитель дробной части - точка")
    return SCAN_REQUEST_RADIUS


def inline_location_handler(update: Update, context: CallbackContext):
    context.chat_data["lon"] = update.effective_message.location.longitude
    context.chat_data["lat"] = update.effective_message.location.latitude
    return request_radius(update, context)


def manual_location_handler(update: Update, context: CallbackContext):
    lat, lon = update.effective_message.text.split(",")
    context.chat_data["lon"] = float(lon)
    context.chat_data["lat"] = float(lat)
    return request_radius(update, context)


@inject_user
def radius_handler(update: Update, context: CallbackContext, user: TelegramUser):
    radius = float(update.effective_message.text)
    count = set_atms(user, context.chat_data["lon"], context.chat_data["lat"], radius)
    update.effective_message.reply_text(text=f"Готово, слежение за {count} банкоматом(ами) включено 😉")
    return ConversationHandler.END


@inject_user
def stop_handler(update: Update, context: CallbackContext, user: TelegramUser):
    user.notify_settings.all().delete()
    update.effective_message.reply_text(text="Готово, больше никаких уведомлений, приходи, когда надумаешь 😉")


def configure_bot() -> Updater:
    updater = Updater(token=settings.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(CommandHandler("payment", payment_handler))
    dispatcher.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("currency", currency_handler)],
            states={
                CURRENCY_SAVE: [MessageHandler(Filters.text & ~Filters.command, currency_finish_handler)],
            },
            fallbacks=[MessageHandler(Filters.all, fallback_exit_handler)],
            allow_reentry=True,
        )
    )
    dispatcher.add_handler(
        ConversationHandler(
            entry_points=[CommandHandler("scan", scan_handler)],
            states={
                SCAN_REQUEST_POS: [
                    MessageHandler(Filters.location, inline_location_handler, pass_user_data=True),
                    MessageHandler(
                        Filters.regex(r"^\d+\.?\d*\s*,\s*\d+\.?\d*$") & ~Filters.command,
                        manual_location_handler,
                    ),
                ],
                SCAN_REQUEST_RADIUS: [MessageHandler(Filters.regex(r"^\d+\.?\d*$") & ~Filters.command, radius_handler)],
            },
            fallbacks=[MessageHandler(Filters.all, fallback_exit_handler)],
            allow_reentry=True,
        )
    )
    dispatcher.add_handler(CommandHandler("stop", stop_handler))
    dispatcher.add_handler(MessageHandler(Filters.all, help_command))

    return updater
