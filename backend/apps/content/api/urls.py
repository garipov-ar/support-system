from django.urls import path
from .views import NavigationView, CategoryDetailView, SearchView, DocumentDetailView

urlpatterns = [
    path("navigation/", NavigationView.as_view()),
    path("category/<int:category_id>/", CategoryDetailView.as_view()),
    path("document/<int:document_id>/", DocumentDetailView.as_view()),
    path("search/", SearchView.as_view()),
]
