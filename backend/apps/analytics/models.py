from django.db import models
from django.conf import settings

class BotInteraction(models.Model):
    user = models.ForeignKey('bot.BotUser', on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    django_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='interactions', null=True, blank=True)
    action_type = models.CharField(max_length=50) # command, callback, text, web_view
    path = models.CharField(max_length=255, blank=True, null=True) # e.g. "cat:1" or "/search"
    response_time_ms = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Взаимодействие'
        verbose_name_plural = 'Статистика'

    def __str__(self):
        if self.user:
            identity = f"BotUser: {self.user.first_name or self.user.telegram_id}"
        elif self.django_user:
            identity = f"WebUser: {self.django_user.username}"
        else:
            identity = "Anonymous"
        return f"{identity} - {self.action_type} at {self.timestamp}"

class SearchQueryLog(models.Model):
    query_text = models.CharField(max_length=255)
    results_count = models.IntegerField(default=0)
    user = models.ForeignKey('bot.BotUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='search_logs')
    django_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='search_logs')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            user_display = self.user.first_name if self.user.first_name else "BotUser"
        elif self.django_user:
            user_display = self.django_user.username
        else:
             user_display = "Unknown"
        return f"'{self.query_text}' by {user_display}"

class AuditLog(models.Model):
    ACTION_TYPES = [
        ('LOGIN', 'Вход в систему'),
        ('LOGOUT', 'Выход из системы'),
        ('DOCUMENT_CREATE', 'Создание документа'),
        ('DOCUMENT_EDIT', 'Редактирование документа'),
        ('DOCUMENT_DELETE', 'Удаление документа'),
        ('CATEGORY_CREATE', 'Создание категории'),
        ('CATEGORY_EDIT', 'Редактирование категории'),
        ('CATEGORY_DELETE', 'Удаление категории'),
        ('BOT_REQUEST', 'Запрос в боте'),
        ('FILE_DOWNLOAD', 'Скачивание файла'),
        ('UNAUTHORIZED_ACCESS', 'Попытка несанкционированного доступа'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    bot_user = models.ForeignKey('bot.BotUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    object_type = models.CharField(max_length=50, blank=True)
    object_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
    
    def __str__(self):
        user_str = self.user.username if self.user else (self.bot_user.first_name if self.bot_user else "System")
        return f"{self.get_action_type_display()} - {user_str} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
