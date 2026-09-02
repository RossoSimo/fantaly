from django.urls import path

from . import views

app_name = 'auction'

urlpatterns = [
    path('<int:league_pk>/', views.AuctionDashboardView.as_view(), name='dashboard'),
    path('<int:league_pk>/nominate/', views.NominatePlayerView.as_view(), name='nominate'),
    path(
        '<int:league_pk>/nominations/<int:nomination_pk>/confirm/',
        views.ConfirmPurchaseView.as_view(),
        name='confirm_purchase',
    ),
]
