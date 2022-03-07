import hashlib

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View

from apps.payments.models import Payment
from apps.tgbot.models import TelegramUser


def payment_view(request, tuid: str):
    user = get_object_or_404(TelegramUser.objects.filter(has_subscription=False), id=tuid)
    return render(request, "payments/payment.html", {"user": user})


class YoomoneyNotificationView(View):
    """
    Api for retrieving notifications from yoomoney service
    https://yoomoney.ru/docs/wallet/using-api/notification-p2p-incoming
    """

    def is_valid(self, data: dict) -> bool:
        params_string = "&".join(
            (
                data.get(param, "")
                for param in [
                    "notification_type",
                    "operation_id",
                    "amount",
                    "currency",
                    "datetime",
                    "sender",
                    "codepro",
                ]
            )
        )
        params_string += f"&{settings.YOOMONEY_NOTIFICATION_SECRET}&"
        params_string += data.get("label", "")
        sha1_hash = hashlib.sha1()
        sha1_hash.update(params_string.encode("utf-8"))
        return sha1_hash.hexdigest() == data.get("sha1_hash", "")

    def post(self, request, *args, **kwargs):
        user = TelegramUser.objects.filter(id=request.POST.get("label")).first()
        suspicious = (
            self.is_valid(request.POST)
            or request.POST.get("codepro") == "true"
            or request.POST.get("unaccepted") == "true"
            or not user
        )
        Payment.objects.create(data=request.POST, suspicious=suspicious)

        if not suspicious:
            user.has_subscription = True
            user.save(update_fields=["has_subscription"])

        return HttpResponse()
