from django.contrib import admin
from django.db.models import Count

from apps.tgbot.models import TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["id", "has_subscription", "atm_count", "extra_data"]
    filter_horizontal = ["atms"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(atm_count=Count("atms"))

    @admin.display(description="atm_count", ordering="atm_count")
    def atm_count(self, obj: TelegramUser):
        return obj.atm_count
