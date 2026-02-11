from rest_framework.views import APIView
from rest_framework.response import Response
from apps.content import services

class NavigationView(APIView):
    def get(self, request):
        categories = services.get_root_categories()
        return Response([
            {"id": c.id, "title": c.title}
            for c in categories
        ])


class CategoryDetailView(APIView):
    def get(self, request, category_id):
        data = services.get_category_details(category_id)
        return Response(data)


class DocumentDetailView(APIView):
    def get(self, request, document_id):
        data = services.get_document_details(document_id)
        return Response(data)


class SearchView(APIView):
    def get(self, request):
        query = request.GET.get("q", "")
        results = services.search_content(query)
        return Response(results)
