from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import Group
from .models import User, GroupProxy

admin.site.unregister(Group)

@admin.register(GroupProxy)
class GroupProxyAdmin(BaseGroupAdmin):
    pass


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "telegram_id", "is_staff", "is_superuser")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "first_name", "last_name", "email", "telegram_id")
    
    # Configuration for the "Change User" page
    # Configuration for the "Change User" page
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "email")}),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        ("Effective Permissions", {
            "fields": ("effective_permissions_display",),
            "classes": ("collapse",),
            "description": "Shows all permission this user has, including those inherited from groups."
        }),
    )
    
    # Configuration for the "Add User" page
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {"fields": ("email", "first_name", "last_name", "telegram_id")}),
    )

    readonly_fields = ("effective_permissions_display",)

    def effective_permissions_display(self, obj):
        from django.utils.html import format_html
        perms = obj.get_all_permissions()
        if not perms:
            return "No permissions"
        
        # Sort and format
        sorted_perms = sorted(perms)
        html_list = ["<ul>"]
        for perm_str in sorted_perms:
            app_label, codename = perm_str.split('.')
            html_list.append(f"<li>{app_label} | {codename}</li>")
        html_list.append("</ul>")
        
        return format_html("".join(html_list))
    
    effective_permissions_display.short_description = "All Effective Permissions"

    def has_change_permission(self, request, obj=None):
        # Allow default check first
        has_perm = super().has_change_permission(request, obj)
        if not has_perm:
            return False
        
        # Security: Non-superusers cannot edit superusers
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
            
        return True

    def has_delete_permission(self, request, obj=None):
        # Allow default check first
        has_perm = super().has_delete_permission(request, obj)
        if not has_perm:
            return False

        # Security: Non-superusers cannot delete superusers
        if obj and obj.is_superuser and not request.user.is_superuser:
            return False
            
        return True
