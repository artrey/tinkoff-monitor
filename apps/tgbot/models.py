from django.db import models

from apps.monitor.models import ATM
from apps.tgbot.drf_json_encoder import JSONEncoder


class TelegramUser(models.Model):
    id = models.CharField(max_length=32, primary_key=True)
    extra_data = models.JSONField(encoder=JSONEncoder, null=True, blank=True)
    has_subscription = models.BooleanField(default=False)
    atms = models.ManyToManyField(ATM, related_name="subscribers", blank=True)

    def __str__(self) -> str:
        return self.id
