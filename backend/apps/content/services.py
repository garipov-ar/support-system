from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.content.models import Category, DocumentVersion
from django.core.cache import cache

def get_root_categories():
    """Calculates the list of root categories visible in the bot."""
    key = "category_root"
    cached = cache.get(key)
    if cached:
        return cached

    result = list(Category.objects.filter(parent=None, is_folder=True, visible_in_bot=True).order_by("order"))
    cache.set(key, result, timeout=60*15)
    return result

def get_category_details(category_id):
    """
    Returns full details for a category:
    - The category itself
    - Children documents (files)
    - Subcategories (folders)
    - Breadcrumbs (path)
    """
    key = f"category_{category_id}_details"
    cached = cache.get(key)
    if cached:
        return cached

    category = get_object_or_404(Category, id=category_id)
    
    # Documents (is_folder=False)
    document_nodes = Category.objects.filter(parent=category, is_folder=False, visible_in_bot=True).order_by("order")
    
    documents_data = []
    for node in document_nodes:
        version = (
            DocumentVersion.objects
            .filter(content_node=node)
            .order_by("-created_at")
            .first()
        )
        documents_data.append({
            "id": node.id,
            "title": node.title,
            "file_path": version.file.name if version else None
        })

    # Subcategories (is_folder=True)
    subcategories = Category.objects.filter(parent=category, is_folder=True, visible_in_bot=True).order_by("order")
    
    result = {
        "id": category.id,
        "category": category.title,
        "path": [c.title for c in category.get_ancestors()],
        "parent_id": category.parent.id if category.parent else None,
        "subcategories": [
            {"id": s.id, "title": s.title} for s in subcategories
        ],
        "documents": documents_data
    }
    
    cache.set(key, result, timeout=60*15)
    return result

def get_document_details(document_id):
    """
    Returns details for a specific document node.
    """
    document_node = get_object_or_404(Category, id=document_id, is_folder=False)
    
    version = (
        DocumentVersion.objects
        .filter(content_node=document_node)
        .order_by("-created_at")
        .first()
    )
    
    return {
        "id": document_node.id,
        "title": document_node.title,
        "description": document_node.description,
        "category_id": document_node.parent.id if document_node.parent else None,
        "file_path": version.file.name if version else None,
        "version": version.version if version else None,
        "telegram_file_id": version.telegram_file_id if version else None,
        "equipment_name": document_node.equipment.name if document_node.equipment else None
    }

def search_content(query):
    """
    Searches for documents by title or description.
    """
    if not query:
        return []

    document_nodes = Category.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query),
        is_folder=False,
        visible_in_bot=True
    ).select_related('parent')[:10]

    return [
        {
            "id": node.id,
            "title": node.title,
            "category_id": node.parent.id if node.parent else None
        }
        for node in document_nodes
    ]
