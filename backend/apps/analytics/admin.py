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

    def changelist_view(self, request, extra_context=None):
        return self.dashboard_view(request)

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
            BotInteraction.objects.filter(user__isnull=False)
            .values('user__first_name', 'user__last_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        active_web_users = (
            BotInteraction.objects.filter(django_user__isnull=False)
            .values('django_user__username', 'django_user__first_name', 'django_user__last_name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )

        # Calculate storage usage
        total_size_bytes = 0
        from apps.content.models import DocumentVersion
        import os

        # We need to be careful with file access
        # Optimization: Maybe raw SQL query for efficient iteration?
        # Or standard loop for now as project is small.
        for doc_version in DocumentVersion.objects.all():
             try:
                 if doc_version.file and os.path.exists(doc_version.file.path):
                     total_size_bytes += doc_version.file.size
             except Exception:
                 pass # File might be missing
        
        total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
        total_size_gb = round(total_size_bytes / (1024 * 1024 * 1024), 4)

        # User Stats
        from apps.bot.models import BotUser
        total_users = BotUser.objects.count()
        new_users_7d = BotUser.objects.filter(created_at__gte=timezone.now() - timedelta(days=7)).count()
        new_users_30d = BotUser.objects.filter(created_at__gte=timezone.now() - timedelta(days=30)).count()

        # Failed Searches
        failed_searches = (
            SearchQueryLog.objects.filter(results_count=0)
            .values('query_text')
            .annotate(count=Count('id'))
            .order_by('-count')[:5]
        )

        # Popular Content (Categories and Docs)
        popular_content = []
        path_counts = (
            BotInteraction.objects.filter(path__isnull=False)
            .values('path')
            .annotate(count=Count('id'))
            .order_by('-count')[:20] 
        )
        
        # Resolve names for popular content
        from apps.content.models import Category
        # Document model is deprecated; documents are now Category nodes (is_folder=False)
        
        for item in path_counts:
            path = item['path']
            name = path
            type_label = "?"
            
            try:
                # Both cat: and doc: refer to Category model IDs now
                obj_id = int(path.split(':')[-1])
                
                if path.startswith('cat:'):
                    cat = Category.objects.filter(id=obj_id).first()
                    if cat:
                        name = cat.title
                        type_label = "Категория"
                elif path.startswith('doc:'):
                    # Priority 1: New System - Document Node (Category with is_folder=False)
                    doc_node = Category.objects.filter(id=obj_id, is_folder=False).first()
                    if doc_node:
                        name = doc_node.title
                        type_label = "Документ"
                    else:
                        # Fallback - might be a Category referenced as doc
                        cat_fallback = Category.objects.filter(id=obj_id).first()
                        if cat_fallback:
                            name = cat_fallback.title
                            type_label = "Категория (как документ)"
                elif path.startswith('sub:toggle:'):
                     continue 
            except Exception:
                pass
            
            if path.startswith('cat:') or path.startswith('doc:'):
                 popular_content.append({'name': name, 'type': type_label, 'count': item['count'], 'path': path})
        
        popular_content = popular_content[:5]

        # Error Rate
        # Count errors in AuditLogs (where details has 'error')
        # JSONField lookup for Postgres
        error_count = AuditLog.objects.filter(details__has_key='error').count()
        total_requests = BotInteraction.objects.count()
        error_rate = 0
        if total_requests > 0:
            error_rate = round((error_count / total_requests) * 100, 2)

        import json
        
        context = {
            **self.admin_site.each_context(request),
            'title': 'Дашборд аналитики',
            'interactions_labels': json.dumps([str(item['day']) for item in interactions_per_day]),
            'interactions_data': json.dumps([item['count'] for item in interactions_per_day]),
            'avg_time_labels': json.dumps([str(item['day']) for item in avg_response_time]),
            'avg_time_data': json.dumps([float(item['avg_time'] or 0) for item in avg_response_time]),
            'top_searches': top_searches,
            'active_users': [
                {'name': f"{item['user__first_name']} {item['user__last_name'] or ''}".strip(), 'count': item['count']}
                for item in active_users
            ],
            'active_web_users': [
                {'name': f"{item['django_user__first_name']} {item['django_user__last_name']} ({item['django_user__username']})".strip(), 'count': item['count']}
                for item in active_web_users
            ],
            'total_size_mb': total_size_mb,
            'total_size_gb': total_size_gb,
            
            # New Metrics
            'user_stats': {
                'total': total_users,
                'new_7d': new_users_7d,
                'new_30d': new_users_30d
            },
            'failed_searches': failed_searches,
            'popular_content': popular_content,
            'system_health': {
                'error_count': error_count,
                'error_rate': error_rate
            }
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
    list_display = ('action_type', 'get_user_display', 'object_type', 'object_id', 'ip_address', 'timestamp', 'get_details_display')
    list_filter = ('action_type', 'timestamp', 'object_type')
    search_fields = ('user__username', 'bot_user__first_name', 'details')
    readonly_fields = ('user', 'bot_user', 'action_type', 'object_type', 'object_id', 'details', 'ip_address', 'timestamp', 'get_details_display')
    
    def get_details_display(self, obj):
        import json
        details = obj.details
        if not details:
            return "-"
        
        # If details is a string, try to parse it
        if isinstance(details, str):
            try:
                details = json.loads(details)
            except:
                return details

        # Check for bot path patterns
        path = details.get('path')
        if path:
            if path.startswith('sub:toggle:'):
                return f"Подписка/Отписка (Категория ID: {path.split(':')[-1]})"
            if path.startswith('cat:'):
                return f"Просмотр категории (ID: {path.split(':')[-1]})"
            if path.startswith('doc:'):
                return f"Скачивание документа (ID: {path.split(':')[-1]})"
            if path.startswith('back:'):
                return f"Назад (ID: {path.split(':')[-1]})"
            if path == 'start':
                return "Запуск бота /start"
            if path == 'search':
                return "Поиск"
            return f"Действие: {path}"

        # Search queries
        query = details.get('query')
        if query:
            count = details.get('results', 0)
            return f"Поиск: '{query}' (Найдено: {count})"
            
        # Admin actions
        category_title = details.get('category_title')
        version = details.get('version')
        if version and category_title:
             return f"Версия: {version} (Категория: {category_title})"
             
        title = details.get('title')
        if title:
            return f"Заголовок: {title}"

        # Fallback to json string
        return str(details)
    get_details_display.short_description = 'Детали'

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
