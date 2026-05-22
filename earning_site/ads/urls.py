from django.urls import path
from ads.views import watch_ad_view
app_name = 'ads'
urlpatterns = [
    # ✅ Watch Ad - one ad per plan per day
    path('watch-ad/<int:plan_id>/', watch_ad_view, name='watch_ad'),
]
