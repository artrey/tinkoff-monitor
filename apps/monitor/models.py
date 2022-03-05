from django.db import models


class ATM(models.Model):
    address = models.TextField()
    worktime = models.CharField(max_length=256)
    lon = models.DecimalField(max_digits=18, decimal_places=15)
    lat = models.DecimalField(max_digits=18, decimal_places=15)

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
