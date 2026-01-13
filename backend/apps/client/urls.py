from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'client'

urlpatterns = [
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('support/', views.SupportView.as_view(), name='support'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', views.HomeView.as_view(), name='home'),
    path('category/<int:pk>/', views.CategoryDetailView.as_view(), name='category'),
    path('document/<int:pk>/', views.DocumentDetailView.as_view(), name='document'),
    path('search/', views.SearchView.as_view(), name='search'),
]
