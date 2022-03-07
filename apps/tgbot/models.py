from django.db import models

from apps.drf_json_encoder import JSONEncoder
from apps.monitor.models import ATM


class TelegramUser(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    extra_data = models.JSONField(encoder=JSONEncoder, null=True, blank=True)
    has_subscription = models.BooleanField(default=False)
    atms = models.ManyToManyField(ATM, related_name="subscribers", through="NotifySettings")

    def __str__(self) -> str:
        return self.id


class NotifySettings(models.Model):
    atm = models.ForeignKey(ATM, on_delete=models.CASCADE, related_name="notify_settings")
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name="notify_settings")
    need_rub = models.BooleanField(default=False)
    need_usd = models.BooleanField(default=False)
    need_eur = models.BooleanField(default=False)
