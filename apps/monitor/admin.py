from django.contrib import admin
from django.db.models import Count
from django.utils.safestring import mark_safe

from apps.monitor.models import ATM, ATMHistoryInfo, ATMLastInfo
from apps.tgbot.models import NotifySettings


class ATMLastInfoInline(admin.StackedInline):
    model = ATMLastInfo
    extra = 0


class ATMHistoryInfoInline(admin.TabularInline):
    model = ATMHistoryInfo
    extra = 0
    readonly_fields = ["created_at"]

    def has_change_permission(self, request, obj=None):
        return False


class NotifySettingsInline(admin.TabularInline):
    model = NotifySettings
    extra = 0


@admin.register(ATM)
class ATMAdmin(admin.ModelAdmin):
    list_display = ["id", "address", "on_map", "rub", "usd", "eur", "updated_at", "subscribers_count"]
    list_display_links = ["id", "address"]
    list_select_related = ["last_info"]
    search_fields = ["address"]
    readonly_fields = ["on_map"]
    inlines = [ATMLastInfoInline, NotifySettingsInline, ATMHistoryInfoInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(subscribers_count=Count("subscribers"))

    @admin.display
    def on_map(self, obj: ATM):
        return mark_safe(
            "<a target='_blank' rel='noopener noreferrer' href='https://www.tinkoff.ru/maps/atm/?"
            f"latitude={obj.lat.normalize()}&longitude={obj.lon.normalize()}&zoom=16&partner=tcs'>"
            f"На карте</a>"
        )

    @admin.display(description="rub", ordering="last_info__rub")
    def rub(self, obj: ATM):
        return obj.last_info.rub

    @admin.display(description="usd", ordering="last_info__usd")
    def usd(self, obj: ATM):
        return obj.last_info.usd

    @admin.display(description="eur", ordering="last_info__eur")
    def eur(self, obj: ATM):
        return obj.last_info.eur

    @admin.display(description="updated at", ordering="last_info__updated_at")
    def updated_at(self, obj: ATM):
        return obj.last_info.updated_at

    @admin.display(description="subscribers", ordering="subscribers_count")
    def subscribers_count(self, obj: ATM):
        return obj.subscribers_count


@admin.register(ATMHistoryInfo)
class ATMHistoryInfoAdmin(admin.ModelAdmin):
    list_display = ["atm", "rub", "usd", "eur", "created_at"]
    list_select_related = ["atm"]

    def has_change_permission(self, request, obj=None):
        return False
