from django.urls import path

from . import views

app_name = 'players'

urlpatterns = [
    path('', views.PlayerListView.as_view(), name='list'),
    path('new/', views.PlayerCreateView.as_view(), name='create'),
    path('<int:pk>/', views.PlayerDetailView.as_view(), name='detail'),
]