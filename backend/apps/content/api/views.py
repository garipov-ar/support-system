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

        return Response({
            "category": category.title,
            "documents": result
        })


class SearchView(APIView):
    def get(self, request):
        query = request.GET.get("q", "")
        if not query:
            return Response([])

        documents = Document.objects.filter(title__icontains=query)[:10]

        result = []
        for d in documents:
            version = (
                DocumentVersion.objects
                .filter(document=d)
                .order_by("-created_at")
                .first()
            )
            if version:
                result.append({
                    "title": d.title,
                    "file_path": version.file.name
                })

        return Response(result)
