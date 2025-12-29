from django.db import models

class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    title = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", null=True, blank=True,
        related_name="children", on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField(default=0)
    visible_in_bot = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class Document(models.Model):
    class DocType(models.TextChoices):
        INSTRUCTION = "instruction", "Инструкция"
        FIRMWARE = "firmware", "Прошивка"
        CONFIG = "config", "Конфигурация"
        PRICE = "price", "Прайс-лист"

    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT)
    doc_type = models.CharField(max_length=20, choices=DocType.choices)

class DocumentVersion(models.Model):
    document = models.ForeignKey(
        Document,
        related_name="versions",
        on_delete=models.CASCADE
    )
    version = models.CharField(max_length=50)
    file = models.FileField(upload_to="documents/")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Версия документа"
        verbose_name_plural = "Версии документов"

    def __str__(self):
        return f"{self.document.title} v{self.version}"
