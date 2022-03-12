from typing import Type

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


def money2str(value: int) -> str:
    if value >= 1000:
        return f"{value // 1000} {value % 1000:03}"
    return str(value)


def message_threshold(value: int, threshold: int) -> str:
    if value >= threshold:
        return f"более {money2str(threshold)}"
    return money2str(value)


class ATM(models.Model):
    address = models.TextField()
    worktime = models.CharField(max_length=256)
    lon = models.DecimalField(max_digits=18, decimal_places=15)
    lat = models.DecimalField(max_digits=18, decimal_places=15)

    def update_currencies(self, rub: int, usd: int, eur: int):
        ATMLastInfo.objects.filter(atm_id=self.id).update(rub=rub, usd=usd, eur=eur, updated_at=timezone.now())
        ATMHistoryInfo.objects.create(atm_id=self.id, rub=rub, usd=usd, eur=eur)

    @property
    def info_message_markdown(self) -> str:
        return f"""
*{self.address}*

*Время работы:* {self.worktime}

[Смотреть на карте](https://www.tinkoff.ru/maps/atm/?latitude={self.lat.normalize()}&longitude={self.lon.normalize()}&zoom=16&partner=tcs)

*RUB:* {message_threshold(self.last_info.rub, 300000)} ₽
*USD:* {message_threshold(self.last_info.usd, 5000)} $
*EUR:* {message_threshold(self.last_info.eur, 5000)} €
        """  # noqa: E501

    def __str__(self) -> str:
        return f"{self.id} | {self.address}"


class MoneyMixin(models.Model):
    rub = models.IntegerField(default=0)
    usd = models.IntegerField(default=0)
    eur = models.IntegerField(default=0)

    class Meta:
        abstract = True


class ATMLastInfo(MoneyMixin, models.Model):
    atm = models.OneToOneField(ATM, on_delete=models.CASCADE, related_name="last_info", primary_key=True)
    updated_at = models.DateTimeField(auto_now=True)
    out_per_transaction = models.TextField(null=True, blank=True)
    out_banknotes = models.TextField(null=True, blank=True)
    in_banknotes = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.atm)


class ATMHistoryInfo(MoneyMixin, models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    atm = models.ForeignKey(ATM, on_delete=models.CASCADE, related_name="history")

    def __str__(self) -> str:
        return str(self.created_at)


@receiver(post_save, sender=ATM, dispatch_uid="create_atm_last_info")
def create_atm_last_info(sender: Type[ATM], instance: ATM, created: bool, **kwargs):
    if not created:
        return
    ATMLastInfo.objects.create(atm=instance)
