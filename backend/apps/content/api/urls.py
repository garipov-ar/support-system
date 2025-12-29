from django.urls import path
from .views import NavigationView, CategoryDetailView, SearchView

urlpatterns = [
    path("navigation/", NavigationView.as_view()),
    path("category/<int:category_id>/", CategoryDetailView.as_view()),
    path("search/", SearchView.as_view()),
]
