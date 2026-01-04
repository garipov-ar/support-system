from django.db import models
from django.conf import settings

class BotInteraction(models.Model):
    user = models.ForeignKey('bot.BotUser', on_delete=models.CASCADE, related_name='interactions')
    action_type = models.CharField(max_length=50) # command, callback, text
    path = models.CharField(max_length=255, blank=True, null=True) # e.g. "cat:1" or "/search"
    response_time_ms = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.first_name or self.user.telegram_id} - {self.action_type} at {self.timestamp}"

class SearchQueryLog(models.Model):
    query_text = models.CharField(max_length=255)
    results_count = models.IntegerField(default=0)
    user = models.ForeignKey('bot.BotUser', on_delete=models.SET_NULL, null=True, related_name='search_logs')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_display = self.user.first_name if self.user and self.user.first_name else "Unknown"
        return f"'{self.query_text}' by {user_display}"
