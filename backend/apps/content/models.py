from django.db import models

class Equipment(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"


from mptt.models import MPTTModel, TreeForeignKey


class Category(MPTTModel):
    title = models.CharField(max_length=255)
    parent = TreeForeignKey(
        "self", null=True, blank=True,
        related_name="children", on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField(default=0)
    visible_in_bot = models.BooleanField(default=True)
    
    # Unified fields
    is_folder = models.BooleanField(default=True, verbose_name="Это папка")
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Оборудование")
    description = models.TextField(verbose_name="Описание", blank=True)

    class MPTTMeta:
        order_insertion_by = ["order"]

    class Meta:
        verbose_name = "Узел контента"
        verbose_name_plural = "Дерево контента"

    def __str__(self):
        prefix = "📁" if self.is_folder else "📄"
        return f"{prefix} {self.title}"


class Document(models.Model):
    """
    DEPRECATED: Заменено на Category(is_folder=False)
    """
    title = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(verbose_name="Описание", blank=True)

    class Meta:
        verbose_name = "Документ (УСТАРЕЛО)"
        verbose_name_plural = "Документы (УСТАРЕЛО)"

    def __str__(self):
        return self.title

class DocumentVersion(models.Model):
    # document = models.ForeignKey(
    #     Document,
    #     related_name="versions",
    #     on_delete=models.CASCADE
    # )
    
    # Переход на новую систему
    content_node = models.ForeignKey(
        Category,
        related_name="versions",
        on_delete=models.CASCADE,
        null=True, # Временно для миграции
        blank=True
    )
    
    version = models.CharField(max_length=50)
    file = models.FileField(upload_to="documents/")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=255)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Версия файла"
        verbose_name_plural = "Версии файлов"

    def __str__(self):
        node_title = self.content_node.title if self.content_node else "Без узла"
        return f"{node_title} v{self.version}"
