from django.urls import path
from wallet.views import withdraw_view

urlpatterns = [
    path('withdraw/', withdraw_view, name='withdraw'),
]
