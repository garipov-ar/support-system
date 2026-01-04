from django.db import models


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
