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


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "equipment", "category")
    list_filter = ("equipment",)
    search_fields = ("title",)
    inlines = [DocumentVersionInline]


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = ("document", "version", "created_at", "author")
    list_filter = ("document",)
