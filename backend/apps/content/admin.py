from django.contrib import admin
from django.utils.html import mark_safe
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Equipment, Category, Document, DocumentVersion


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


from mptt.admin import DraggableMPTTAdmin


@admin.register(Category)
class CategoryAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    list_display = ("tree_actions", "indented_title", "visible_in_bot")
    list_display_links = ("indented_title",)
    list_filter = ("visible_in_bot",)
    search_fields = ("title",)


# 🔹 Inline ОБЯЗАТЕЛЬНО объявляется ДО DocumentAdmin
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


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "equipment", "category")
    list_filter = ("equipment",)
    search_fields = ("title",)
    inlines = [DocumentVersionInline]
    
    # Enable CKEditor for description
    formfield_overrides = {
        Document.description.__class__: {'widget': CKEditor5Widget(config_name='extends')},
    }

    def save_formset(self, request, form, formset, change):
        """
        Переопределяем сохранение inline-форм (версий документов),
        чтобы автоматически проставить автора текущим пользователем.
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, DocumentVersion):
                # Если автор не указан (новая запись), ставим текущего юзера
                if not instance.author:
                    instance.author = request.user.username or "Admin"
            instance.save()
        formset.save_m2m()


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version", "created_at", "author")
    list_filter = ("document",)
