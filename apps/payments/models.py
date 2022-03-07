from django.db import models

from apps.drf_json_encoder import JSONEncoder


class Payment(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    data = models.JSONField(encoder=JSONEncoder, null=True, blank=True)
    suspicious = models.BooleanField(default=False)
