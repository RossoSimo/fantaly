from django.urls import path

from . import views

app_name = 'leagues'

urlpatterns = [
    path('', views.LeagueListView.as_view(), name='list'),
    path('new/', views.LeagueCreateView.as_view(), name='create'),
    path('<int:pk>/', views.LeagueDetailView.as_view(), name='detail'),
    path('<int:pk>/managers/add/', views.AddManagerView.as_view(), name='add_manager'),
]