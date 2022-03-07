from django.contrib import admin

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["id", "created_at", "suspicious", "data"]
    list_filter = ["created_at", "suspicious"]
    readonly_fields = ["data"]

    def has_add_permission(self, request):
        return False
