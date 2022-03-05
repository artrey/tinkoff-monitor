from django.contrib import admin
from django.db.models import Count

from apps.monitor.models import ATM, ATMHistoryInfo, ATMLastInfo


class ATMLastInfoInline(admin.StackedInline):
    model = ATMLastInfo
    extra = 0


class ATMHistoryInfoInline(admin.TabularInline):
    model = ATMHistoryInfo
    extra = 0
    readonly_fields = ["created_at"]

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ATM)
class ATMAdmin(admin.ModelAdmin):
    list_display = ["id", "address", "rub", "usd", "eur", "updated_at", "subscribers_count"]
    list_display_links = ["id", "address"]
    list_select_related = ["last_info"]
    inlines = [ATMLastInfoInline, ATMHistoryInfoInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(subscribers_count=Count("subscribers"))

    @admin.display(description="rub", ordering="last_info__rub")
    def rub(self, obj: ATM):
        return obj.last_info.rub

    @admin.display(description="usd", ordering="last_info__usd")
    def usd(self, obj: ATM):
        return obj.last_info.usd

    @admin.display(description="eur", ordering="last_info__eur")
    def eur(self, obj: ATM):
        return obj.last_info.eur

    @admin.display(description="updated_at", ordering="last_info__updated_at")
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
