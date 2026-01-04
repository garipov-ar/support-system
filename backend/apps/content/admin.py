from django.contrib import admin
from .models import Equipment, Category, Document, DocumentVersion


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("title", "parent", "order", "visible_in_bot")
    list_filter = ("visible_in_bot",)
    search_fields = ("title",)
    ordering = ("parent__id", "order")


# 🔹 Inline ОБЯЗАТЕЛЬНО объявляется ДО DocumentAdmin
class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 1
    exclude = ("author",)  # Скрываем поле из формы, так как оно заполняется авто


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "equipment", "category")
    list_filter = ("equipment",)
    search_fields = ("title",)
    inlines = [DocumentVersionInline]

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
