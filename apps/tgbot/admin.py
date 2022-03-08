from django.contrib import admin
from django.db.models import Count

from apps.tgbot.models import NotifySettings, TelegramUser


class NotifySettingsInline(admin.TabularInline):
    model = NotifySettings
    extra = 0


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ["id", "has_subscription", "atm_count", "extra_data"]
    search_fields = ["id", "extra_data__username"]
    inlines = [NotifySettingsInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(atm_count=Count("atms"))

    @admin.display(description="atm count", ordering="atm_count")
    def atm_count(self, obj: TelegramUser):
        return obj.atm_count


@admin.register(NotifySettings)
class NotifySettingsAdmin(admin.ModelAdmin):
    list_display = ["atm", "user", "need_rub", "need_usd", "need_eur"]
    list_select_related = ["atm", "user"]
    search_fields = ["user__id", "user__extra_data__username", "atm__address"]
