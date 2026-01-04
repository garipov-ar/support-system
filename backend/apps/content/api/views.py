from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.content.models import Category, Document, DocumentVersion


class NavigationView(APIView):
    def get(self, request):
        categories = Category.objects.filter(parent=None, visible_in_bot=True).order_by("order")
        return Response([
            {"id": c.id, "title": c.title}
            for c in categories
        ])


class CategoryDetailView(APIView):
    def get(self, request, category_id):
        category = get_object_or_404(Category, id=category_id)
        documents = Document.objects.filter(category=category)

        result = []
        for d in documents:
            version = (
                DocumentVersion.objects
                .filter(document=d)
                .order_by("-created_at")
                .first()
            )
            result.append({
                "id": d.id,
                "title": d.title,
                "file_path": version.file.name if version else None
            })

        subcategories = Category.objects.filter(parent=category, visible_in_bot=True).order_by("order")
        
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
        document = get_object_or_404(Document, id=document_id)
        
        version = (
            DocumentVersion.objects
            .filter(document=document)
            .order_by("-created_at")
            .first()
        )
        
        return Response({
            "id": document.id,
            "title": document.title,
            "description": document.description,
            "category_id": document.category.id,
            "file_path": version.file.name if version else None
        })


from django.db.models import Q

class SearchView(APIView):
    def get(self, request):
        query = request.GET.get("q", "")
        if not query:
            return Response([])

        documents = Document.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).select_related('category')[:10]

        return Response([
            {
                "id": d.id,
                "title": d.title,
                "category_id": d.category.id
            }
            for d in documents
        ])
