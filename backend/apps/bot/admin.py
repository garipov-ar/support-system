from django.contrib import admin
from .models import BotUser


@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "last_name", "email", "agreed_to_policy", "created_at")
    list_filter = ("agreed_to_policy", "created_at")
    search_fields = ("telegram_id", "username", "first_name", "last_name", "email")
