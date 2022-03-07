import functools
import logging
import re

from django.conf import settings
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
        " иначе можно не успеть забрать валюту 😱\n\n"
        "За свои услуги я возьму с тебя 100 рублей. Плати один раз - пользуйся всегда 😉",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Банкоматы"), KeyboardButton("Оплата")]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
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


ATM_COMMAND, ATM_ADD, ATM_CONFIGURE, ATM_CONFIGURE_FINISH, ATM_REMOVE, ATM_REMOVE_ALL = range(6)
ATM_COMMANDS_TEXT = {
    ATM_ADD: "Добавить/изменить банкомат",
    # ATM_CONFIGURE: "Настроить банкомат",
    # ATM_REMOVE: "Удалить банкомат",
    ATM_REMOVE_ALL: "Отписаться от всех уведомлений",
}
ATM_TEXT_COMMAND = {v: k for k, v in ATM_COMMANDS_TEXT.items()}


@inject_user
def atm_start_handler(update: Update, context: CallbackContext, user: TelegramUser):
    choices = ReplyKeyboardMarkup(
        [
            [KeyboardButton(ATM_COMMANDS_TEXT[ATM_ADD])],
            [KeyboardButton(ATM_COMMANDS_TEXT[ATM_REMOVE_ALL])],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    update.effective_message.reply_text(
        text="Что требуется сделать?",
        reply_markup=choices,
    )

    return ATM_COMMAND


@inject_user
def atm_command_handler(update: Update, context: CallbackContext, user: TelegramUser):
    command = ATM_TEXT_COMMAND.get(update.effective_message.text)
    if not command:
        return atm_start_handler(update, context)

    message = {
        ATM_ADD: dict(
            text="По какому адресу интересует банкомат? Мне будет проще понять тебя, если ты введешь адрес"
            " (или его часть) как на официальной карте Тинькофф: https://www.tinkoff.ru/maps/atm/",
            reply_markup=ReplyKeyboardRemove(),
        ),
        # ATM_CONFIGURE: "ATM_CONFIGURE",
        # ATM_REMOVE: "ATM_REMOVE",
        ATM_REMOVE_ALL: dict(
            text="Точно хочешь отписаться от всех уведомлений?",
            reply_markup=ReplyKeyboardMarkup(
                [["Да", "Нет"]],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        ),
    }[command]
    update.effective_message.reply_text(**message)
    return command


@inject_user
def atm_add_handler(update: Update, context: CallbackContext, user: TelegramUser):
    atms = ATM.objects.filter(address__icontains=update.effective_message.text).values_list("address", flat=True)[:5]

    if not atms:
        update.effective_message.reply_text(text="Ничего похожего не нахожу... Может другой адрес?")
        return atm_command_handler(update, context)

    choices = ReplyKeyboardMarkup(
        [[KeyboardButton(atm)] for atm in atms],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

    update.effective_message.reply_text(
        text="Что-то из этого?",
        reply_markup=choices,
    )

    return ATM_CONFIGURE


@inject_user
def atm_configure_handler(update: Update, context: CallbackContext, user: TelegramUser):
    atm = ATM.objects.filter(address=update.effective_message.text).first()
    if not atm:
        return atm_command_handler(update, context)

    context.chat_data["atm"] = atm.id
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

    return ATM_CONFIGURE_FINISH


@inject_user
def atm_configure_finish_handler(update: Update, context: CallbackContext, user: TelegramUser):
    atm = ATM.objects.filter(id=context.chat_data["atm"]).first()
    if not atm:
        update.effective_message.reply_text(text="Что-то сломалось... Надо начать сначала")
        return atm_command_handler(update, context)

    need_rub = "₽" in update.effective_message.text
    need_usd = "$" in update.effective_message.text
    need_eur = "€" in update.effective_message.text

    NotifySettings.objects.update_or_create(
        atm=atm,
        user=user,
        defaults=dict(need_rub=need_rub, need_usd=need_usd, need_eur=need_eur),
    )

    roi = "/".join(["₽$€"[idx] for idx, v in enumerate((need_rub, need_usd, need_eur)) if v])
    update.effective_message.reply_text(
        text=f"""
Отлично! Запомнил 😉

Адрес: *{atm.address}*

Интересует: *{roi}*
        """,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="markdown",
    )

    return ATM_COMMAND


@inject_user
def atm_remove_all_handler(update: Update, context: CallbackContext, user: TelegramUser):
    if update.effective_message.text.lower() == "да":
        user.notify_settings.all().delete()
        update.effective_message.reply_text(
            text="Готово, приходи, когда надумаешь 😉",
            reply_markup=ReplyKeyboardRemove(),
        )

    return ATM_COMMAND


def configure_bot() -> Updater:
    updater = Updater(token=settings.TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(
        MessageHandler(
            Filters.regex(re.compile(r"^оплата$", re.IGNORECASE)) & ~Filters.command,
            payment_handler,
        )
    )
    dispatcher.add_handler(
        ConversationHandler(
            entry_points=[
                MessageHandler(
                    Filters.regex(re.compile(r"^банкоматы?$", re.IGNORECASE)) & ~Filters.command,
                    atm_start_handler,
                )
            ],
            states={
                ATM_COMMAND: [MessageHandler(Filters.text & ~Filters.command, atm_command_handler)],
                ATM_ADD: [MessageHandler(Filters.text & ~Filters.command, atm_add_handler)],
                ATM_CONFIGURE: [MessageHandler(Filters.text & ~Filters.command, atm_configure_handler)],
                ATM_CONFIGURE_FINISH: [MessageHandler(Filters.text & ~Filters.command, atm_configure_finish_handler)],
                ATM_REMOVE_ALL: [MessageHandler(Filters.text & ~Filters.command, atm_remove_all_handler)],
            },
            fallbacks=[],
            allow_reentry=True,
        )
    )
    dispatcher.add_handler(MessageHandler(Filters.all, help_command))

    return updater
