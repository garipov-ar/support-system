from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "telegram_id", "is_staff", "is_superuser")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email", "telegram_id")
    
    # Configuration for the "Change User" page
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Custom Fields", {"fields": ("telegram_id",)}),
    )
    
    # Configuration for the "Add User" page
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {"fields": ("email", "first_name", "last_name", "telegram_id")}),
    )
