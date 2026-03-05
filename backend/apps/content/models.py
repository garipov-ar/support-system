from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

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
    description = CKEditor5Field(verbose_name="Описание", blank=True, config_name='extends')

    class MPTTMeta:
        order_insertion_by = ["order"]

    class Meta:
        verbose_name = "Узел контента"
        verbose_name_plural = "Дерево контента"

    def __str__(self):
        prefix = "📁" if self.is_folder else "📄"
        return f"{prefix} {self.title}"

    @property
    def view_count(self):
        """Total views from both web and bot"""
        from apps.analytics.models import BotInteraction
        path_id = f"{'cat' if self.is_folder else 'doc'}:{self.id}"
        return BotInteraction.objects.filter(path=path_id).count()

    @property
    def web_view_count(self):
        from apps.analytics.models import BotInteraction
        path_id = f"{'cat' if self.is_folder else 'doc'}:{self.id}"
        return BotInteraction.objects.filter(path=path_id, action_type='web_view').count()

    @property
    def bot_view_count(self):
        from apps.analytics.models import BotInteraction
        path_id = f"{'cat' if self.is_folder else 'doc'}:{self.id}"
        return BotInteraction.objects.filter(path=path_id, action_type='bot_view').count()




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
    file_size = models.PositiveBigIntegerField(default=0, help_text="Размер файла в байтах")
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.CharField(max_length=255)
    telegram_file_id = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Версия файла"
        verbose_name_plural = "Версии файлов"

    def save(self, *args, **kwargs):
        if self.file:
            try:
                self.file_size = self.file.size
            except Exception:
                pass
        super().save(*args, **kwargs)

    def __str__(self):
        node_title = self.content_node.title if self.content_node else "Без узла"
        return f"{node_title} v{self.version}"

    @property
    def is_image(self):
        if not self.file:
            return False
        return self.extension in ['jpg', 'jpeg', 'png', 'gif', 'webp']

    @property
    def extension(self):
        if not self.file:
            return ""
        return self.file.name.split('.')[-1].lower()


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def clear_content_cache(sender, instance, **kwargs):
    """Clears bot cache when category or document is updated."""
    # 1. Clear root cache (always safe)
    cache.delete("category_root")
    
    # 2. Clear this item's details cache
    cache.delete(f"category_{instance.id}_details")
    
    # 3. Clear parent's details cache (to update children list)
    if instance.parent_id:
        cache.delete(f"category_{instance.parent_id}_details")
    
    # 4. Clear all ancestor caches for safety (since path/breadcrumbs might change)
    for ancestor in instance.get_ancestors():
        cache.delete(f"category_{ancestor.id}_details")
