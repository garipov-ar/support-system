from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import BotInteraction, SearchQueryLog, AuditLog

class BotInteractionAdmin(admin.ModelAdmin):
    list_display = ('user', 'action_type', 'path', 'response_time_ms', 'timestamp')
    list_filter = ('action_type', 'timestamp')
    search_fields = ('user__first_name', 'user__last_name', 'path')
    change_list_template = "admin/analytics/interaction_changelist.html"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.dashboard_view), name='analytics_dashboard'),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        last_7_days = timezone.now() - timedelta(days=7)
        
        interactions_per_day = (
            BotInteraction.objects.filter(timestamp__gte=last_7_days)
            .extra(select={'day': "date(timestamp)"})
            .values('day')
            .annotate(count=Count('id'))
            .order_by('day')
        )

        avg_response_time = (
            BotInteraction.objects.filter(timestamp__gte=last_7_days)
            .extra(select={'day': "date(timestamp)"})
            .values('day')
            .annotate(avg_time=Avg('response_time_ms'))
            .order_by('day')
        )

        top_searches = (
            SearchQueryLog.objects.values('query_text')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        active_users = (
            BotInteraction.objects.values('user__first_name', 'user__last_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        context = {
            **self.admin_site.each_context(request),
            'title': 'Дашборд аналитики',
            'interactions_labels': [str(item['day']) for item in interactions_per_day],
            'interactions_data': [item['count'] for item in interactions_per_day],
            'avg_time_labels': [str(item['day']) for item in avg_response_time],
            'avg_time_data': [float(item['avg_time'] or 0) for item in avg_response_time],
            'top_searches': top_searches,
            'active_users': [
                {'name': f"{item['user__first_name']} {item['user__last_name'] or ''}".strip(), 'count': item['count']}
                for item in active_users
            ],
        }
        return render(request, 'admin/analytics/dashboard.html', context)

@admin.register(SearchQueryLog)
class SearchQueryLogAdmin(admin.ModelAdmin):
    list_display = ('query_text', 'results_count', 'user', 'timestamp')
    list_filter = ('timestamp',)
    search_fields = ('query_text', 'user__first_name', 'user__last_name')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action_type', 'get_user_display', 'object_type', 'object_id', 'ip_address', 'timestamp')
    list_filter = ('action_type', 'timestamp', 'object_type')
    search_fields = ('user__username', 'bot_user__first_name', 'details')
    readonly_fields = ('user', 'bot_user', 'action_type', 'object_type', 'object_id', 'details', 'ip_address', 'timestamp')
    
    def get_user_display(self, obj):
        if obj.user:
            return f"👤 {obj.user.username}"
        elif obj.bot_user:
            return f"🤖 {obj.bot_user.first_name or obj.bot_user.telegram_id}"
        return "System"
    get_user_display.short_description = 'Пользователь'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

admin.site.register(BotInteraction, BotInteractionAdmin)
