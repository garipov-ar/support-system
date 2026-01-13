from django.db import models
from django.conf import settings


class BotUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    agreed_to_policy = models.BooleanField(default=False)
    email = models.EmailField(blank=True, null=True)
    subscribed_categories = models.ManyToManyField(
        "content.Category",
        related_name="subscribers",
        blank=True,
        verbose_name="Подписки на категории"
    )

    def __str__(self):
        return str(self.telegram_id)

class BotStatus(models.Model):
    is_running = models.BooleanField(default=False, verbose_name="Работает")
    last_heartbeat = models.DateTimeField(null=True, blank=True, verbose_name="Последняя активность")
    last_alert_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Последнее уведомление о сбое")
    error_message = models.TextField(blank=True, verbose_name="Последняя ошибка")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Время запуска")
    
    class Meta:
        verbose_name = 'Статус бота'
        verbose_name_plural = 'Статус бота'
    
    def __str__(self):
        status = "🟢 Работает" if self.is_running else "🔴 Не работает"
        return f"{status} (обновлено: {self.last_heartbeat.strftime('%H:%M:%S')})"
    
    @classmethod
    def get_status(cls):
        """Get or create singleton status object"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

class AdminNotificationSettings(models.Model):
    admin_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_settings')
    telegram_id = models.BigIntegerField(null=True, blank=True, verbose_name="Telegram ID для уведомлений")
    notify_on_errors = models.BooleanField(default=True, verbose_name="Уведомлять об ошибках")
    notify_on_unauthorized = models.BooleanField(default=True, verbose_name="Уведомлять о попытках взлома")
    notify_on_bot_down = models.BooleanField(default=True, verbose_name="Уведомлять о сбоях бота")
    
    class Meta:
        verbose_name = 'Настройки уведомлений администратора'
        verbose_name_plural = 'Настройки уведомлений администраторов'
    
    def __str__(self):
        return f"Уведомления для {self.admin_user.username}"

class SupportRequest(models.Model):
    user = models.ForeignKey(BotUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_requests')
    django_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='support_requests')
    message = models.TextField(verbose_name="Сообщение")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создано")
    is_resolved = models.BooleanField(default=False, verbose_name="Решено")
    
    class Meta:
        verbose_name = 'Обращение в поддержку'
        verbose_name_plural = 'Обращения в поддержку'
        ordering = ['-created_at']
    
    def __str__(self):
        user_display = "Unknown"
        if self.user:
            user_display = f"Bot: {self.user}"
        elif self.django_user:
            user_display = f"Web: {self.django_user.username}"
        return f"{user_display} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
