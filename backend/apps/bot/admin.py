from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from datetime import timedelta
from .models import BotUser, BotStatus, AdminNotificationSettings

@admin.register(BotUser)
class BotUserAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'first_name', 'last_name', 'email', 'agreed_to_policy', 'created_at')
    list_filter = ('agreed_to_policy', 'created_at')
    search_fields = ('telegram_id', 'first_name', 'last_name', 'email')
    filter_horizontal = ('subscribed_categories',)

@admin.register(BotStatus)
class BotStatusAdmin(admin.ModelAdmin):
    list_display = ('get_status_display', 'last_heartbeat', 'started_at')
    readonly_fields = ('last_heartbeat',)
    
    def get_status_display(self, obj):
        # Check if heartbeat is recent (within last minute)
        if obj.last_heartbeat:
            time_diff = timezone.now() - obj.last_heartbeat
            if time_diff < timedelta(minutes=1):
                color = 'green'
                status_text = '🟢 Работает'
            else:
                color = 'red'
                status_text = '🔴 Не работает'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span><br>'
                '<small>Последняя активность: {} назад</small>',
                color,
                status_text,
                self._format_timedelta(time_diff)
            )
        return format_html('<span style="color: red;">🔴 Нет данных</span>')
    
    get_status_display.short_description = 'Статус'
    
    def _format_timedelta(self, td):
        seconds = int(td.total_seconds())
        if seconds < 60:
            return f"{seconds} сек"
        elif seconds < 3600:
            return f"{seconds // 60} мин"
        else:
            return f"{seconds // 3600} ч"
    
    def has_add_permission(self, request):
        # Only allow one status object
        return not BotStatus.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(AdminNotificationSettings)
class AdminNotificationSettingsAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'telegram_id', 'notify_on_errors', 'notify_on_unauthorized', 'notify_on_bot_down')
    list_filter = ('notify_on_errors', 'notify_on_unauthorized', 'notify_on_bot_down')
    search_fields = ('admin_user__username',)
    
    fieldsets = (
        ('Администратор', {
            'fields': ('admin_user', 'telegram_id')
        }),
        ('Настройки уведомлений', {
            'fields': ('notify_on_errors', 'notify_on_unauthorized', 'notify_on_bot_down'),
            'description': 'Выберите, о каких событиях вы хотите получать уведомления в Telegram'
        }),
    )
