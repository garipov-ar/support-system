from django.contrib import admin
from django.utils.html import mark_safe
from django.urls import reverse
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Equipment, Category, DocumentVersion


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


from mptt.admin import DraggableMPTTAdmin


# 🔹 Inline ОБЯЗАТЕЛЬНО объявляется ДО DocumentAdmin (и CategoryAdmin, если используется там)
class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 1
    exclude = ("author",)
    readonly_fields = ("file_preview",)

    def file_preview(self, obj):
        if obj.file:
            ext = obj.file.name.split('.')[-1].lower()
            # Images
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                return mark_safe(f'<img src="{obj.file.url}" style="max-height: 150px; border-radius: 4px; box-shadow: 0 0 5px rgba(0,0,0,0.1);" />')
            # PDF
            elif ext == 'pdf':
                return mark_safe(
                    f'<iframe src="{obj.file.url}" width="300" height="200" style="border:1px solid #ddd;"></iframe>'
                    f'<br><a href="{obj.file.url}" target="_blank">Открыть во весь экран</a>'
                )
            # Other Documents
            else:
                return mark_safe(
                    f'<div style="padding: 10px; background: #f8f9fa; border-left: 4px solid #007bff; max-width: 300px;">'
                    f'📄 <strong>{ext.upper()} файл</strong><br>'
                    f'<a href="{obj.file.url}" target="_blank">📥 Скачать / Открыт</a>'
                    f'</div>'
                )
        return "Файл не загружен"
    
    file_preview.short_description = "Предпросмотр / Файл"


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    list_display = ("tree_actions", "indented_title", "is_folder", "visible_in_bot", "get_view_count", "view_on_site")
    list_display_links = ("indented_title",)
    list_filter = ("visible_in_bot", "is_folder")
    search_fields = ("title",)

    def get_view_count(self, obj):
        return f"👁️ {obj.view_count}"
    get_view_count.short_description = "Просмотры"

    def view_on_site(self, obj):
        if obj.is_folder:
            url = reverse('client:category', args=[obj.pk])
        else:
            url = reverse('client:document', args=[obj.pk])
        return mark_safe(f'<a href="{url}" target="_blank" class="button">🔗 На сайт</a>')
    view_on_site.short_description = "Просмотр"

    # Временно убираем инлайн документов из категорий, пока не выполнена миграция
    inlines = [DocumentVersionInline]

    def save_formset(self, request, form, formset, change):
        """
        Populate author for inline DocumentVersion instances.
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, DocumentVersion):
                if not instance.author:
                    instance.author = request.user.username or "Admin"
            instance.save()
        formset.save_m2m()


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("content_node", "version", "created_at", "author")
    list_filter = ("content_node",)
