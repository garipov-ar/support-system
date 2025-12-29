from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        SPECIALIST = "specialist", "Специалист"
        SUPPORT = "support", "Поддержка"
        ADMIN = "admin", "Администратор"

    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
