from django.contrib import admin
from django.contrib.auth import admin as base_admin

from apps.users.models import User


@admin.register(User)
class UserAdmin(base_admin.UserAdmin):
    pass
