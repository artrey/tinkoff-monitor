import functools
import logging
import re

from django.conf import settings
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
    Updater,
)

from apps.tgbot.models import TelegramUser

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
        update.effective_message.reply_text(
            text="Ссылка на оплату: https://yandex.ru\n\nПосле оплаты я начну следить за деньгами для тебя 😉",
            reply_markup=ReplyKeyboardRemove(),
        )


ATM_COMMAND, ATM_ADD, ATM_CONFIGURE, ATM_REMOVE, ATM_REMOVE_ALL = range(5)
ATM_COMMANDS_TEXT = {
    ATM_ADD: "Добавить банкомат",
    ATM_CONFIGURE: "Настроить банкомат",
    ATM_REMOVE: "Удалить банкомат",
    ATM_REMOVE_ALL: "Удалить все",
}
ATM_TEXT_COMMAND = {v: k for k, v in ATM_COMMANDS_TEXT.items()}


@inject_user
def atm_start_handler(update: Update, context: CallbackContext, user: TelegramUser):
    choices = ReplyKeyboardMarkup(
        [
            [KeyboardButton(ATM_COMMANDS_TEXT[ATM_ADD]), KeyboardButton(ATM_COMMANDS_TEXT[ATM_CONFIGURE])],
            [KeyboardButton(ATM_COMMANDS_TEXT[ATM_REMOVE]), KeyboardButton(ATM_COMMANDS_TEXT[ATM_REMOVE_ALL])],
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
        ATM_ADD: "по какому адресу интересует банкомат?",
        ATM_CONFIGURE: "ATM_CONFIGURE",
        ATM_REMOVE: "ATM_REMOVE",
        ATM_REMOVE_ALL: "ATM_REMOVE_ALL",
    }[command]
    update.effective_message.reply_text(text=message, reply_markup=ReplyKeyboardRemove())
    return command


@inject_user
def atm_add_handler(update: Update, context: CallbackContext, user: TelegramUser):
    try:
        record_id = int(update.effective_message.text.split()[0].lstrip("/review"))
        record = Record.objects.exclude(status=Record.Status.CANCELLED).get(id=record_id)
        client_phone_number = TelegramUser.objects.get(id=update.effective_message.from_user.id).phone_number
        if record.client_phone_number != client_phone_number:
            raise ValueError("not authenticated")
    except Exception as ex:
        logger.exception(ex)
        update.effective_message.reply_text(
            "К сожалению, что-то пошло не так :(",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    if Review.objects.filter(record=record).exists():
        update.effective_message.reply_text(
            "Вы уже оставляли отзыв по данному посещению",
            reply_markup=ReplyKeyboardRemove(),
        )
        return ConversationHandler.END

    context.chat_data["review_record_id"] = record_id
    update.effective_message.reply_text(
        "Напишите свои впечатления текстом",
        reply_markup=ReplyKeyboardRemove(),
    )
    return REVIEW_TEXT


def review_text(update: Update, context: CallbackContext, record_id: int):
    context.chat_data["review_text"] = update.effective_message.text
    update.effective_message.reply_text(
        "Укажите оценку от 1 до 5",
        reply_markup=ReplyKeyboardMarkup(
            [["1", "2", "3", "4", "5"]],
            resize_keyboard=True,
            one_time_keyboard=True,
        ),
    )
    return REVIEW_RATING


def review_rating(update: Update, context: CallbackContext, record_id: int):
    rating = int(update.effective_message.text)
    if rating < 1 or rating > 5:
        update.effective_message.reply_text(
            "Оценка должна быть в диапазоне от 1 до 5",
            reply_markup=ReplyKeyboardMarkup(
                [["1", "2", "3", "4", "5"]],
                resize_keyboard=True,
                one_time_keyboard=True,
            ),
        )
        return REVIEW_RATING

    text = context.chat_data["review_text"]
    record = Record.objects.get(id=record_id)
    services_ids = record.services.values_list("id", flat=True)
    Review.objects.create(
        master_id=record.master_id,
        service_id=services_ids[0] if len(services_ids) == 1 else None,
        record=record,
        text=text,
        rating=rating,
    )

    update.effective_message.reply_text(
        "Спасибо за ваш отзыв!",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


def review_fallback(update: Update, context: CallbackContext, record_id: int):
    update.effective_message.reply_text(
        "Вы отменили отзыв по услуге. "
        "Если позднее решите снова оставить его - "
        f"используйте команду /review{record_id}",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


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
                ATM_CONFIGURE: [MessageHandler(Filters.text & ~Filters.command, review_text)],
                ATM_REMOVE: [MessageHandler(Filters.text & ~Filters.command, review_text)],
                ATM_REMOVE_ALL: [MessageHandler(Filters.text & ~Filters.command, review_text)],
                # REVIEW_RATING: [MessageHandler(Filters.regex(r"^\d+$") & ~Filters.command, review_rating)],
            },
            fallbacks=[
                # MessageHandler(Filters.text, atm_fallback)
            ],
            allow_reentry=True,
            # per_message=True,
        )
    )
    dispatcher.add_handler(MessageHandler(Filters.all, help_command))

    return updater
