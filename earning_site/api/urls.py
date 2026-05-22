from django.urls import path

from . import views

app_name = 'api'

urlpatterns = [
    path('me/', views.me, name='me'),
    path('tasks/', views.tasks, name='tasks'),
    path('analytics/', views.analytics, name='analytics'),
    path('notifications/', views.notifications, name='notifications'),
    path('device-token/', views.register_device_token, name='device_token'),
]
