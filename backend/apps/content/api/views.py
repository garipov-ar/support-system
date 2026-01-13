from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.content.models import Category, Document, DocumentVersion


class NavigationView(APIView):
    def get(self, request):
        # Показываем только папки в корне (is_folder=True)
        categories = Category.objects.filter(parent=None, is_folder=True, visible_in_bot=True).order_by("order")
        return Response([
            {"id": c.id, "title": c.title}
            for c in categories
        ])


class CategoryDetailView(APIView):
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        
        # Получаем дочерние узлы-документы (is_folder=False)
        document_nodes = Category.objects.filter(parent=category, is_folder=False, visible_in_bot=True).order_by("order")

        result = []
        for node in document_nodes:
            # Версии теперь связаны через content_node
            version = (
                DocumentVersion.objects
                .filter(content_node=node)
                .order_by("-created_at")
                .first()
            )
            result.append({
                "id": node.id,
                "title": node.title,
                "file_path": version.file.name if version else None
            })

        # Получаем дочерние папки (is_folder=True)
        subcategories = Category.objects.filter(parent=category, is_folder=True, visible_in_bot=True).order_by("order")
        
        return Response({
            "id": category.id,
            "category": category.title,
            "path": [c.title for c in category.get_ancestors()],
            "parent_id": category.parent.id if category.parent else None,
            "subcategories": [
                {"id": s.id, "title": s.title} for s in subcategories
            ],
            "documents": result
        })



class DocumentDetailView(APIView):
    def get(self, request, document_id):
        # Документ теперь это узел Category с is_folder=False
        document_node = get_object_or_404(Category, id=document_id, is_folder=False)
        
        version = (
            DocumentVersion.objects
            .filter(content_node=document_node)
            .order_by("-created_at")
            .first()
        )
        
        return Response({
            "id": document_node.id,
            "title": document_node.title,
            "description": document_node.description,
            "category_id": document_node.parent.id if document_node.parent else None,
            "file_path": version.file.name if version else None,
            "version": version.version if version else None,
            "equipment_name": document_node.equipment.name if document_node.equipment else None
        })


from django.db.models import Q

class SearchView(APIView):
    def get(self, request):
        query = request.GET.get("q", "")
        if not query:
            return Response([])

        # Ищем среди узлов-документов (is_folder=False)
        document_nodes = Category.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query),
            is_folder=False,
            visible_in_bot=True
        ).select_related('parent')[:10]

        return Response([
            {
                "id": node.id,
                "title": node.title,
                "category_id": node.parent.id if node.parent else None
            }
            for node in document_nodes
        ])
