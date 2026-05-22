from django.urls import path

from . import views

app_name = 'rewards'

urlpatterns = [
    path('tasks/', views.tasks_view, name='tasks'),
    path('tasks/<int:task_id>/complete/', views.complete_task_view, name='complete_task'),
    path('bonus/login/', views.claim_login_bonus_view, name='claim_login_bonus'),
    path('referrals/', views.referral_view, name='referrals'),
    path('membership/', views.membership_view, name='membership'),
    path('spin/', views.spin_view, name='spin'),
    path('legal/<slug:page>/', views.legal_page, name='legal'),
    path('admin-analytics/', views.admin_analytics_view, name='admin_analytics'),
    path('advertiser/', views.advertiser_panel_view, name='advertiser_panel'),
    path('advertiser/campaigns/create/', views.create_campaign_view, name='create_campaign'),
    path('advertiser/fund/', views.fund_advertiser_wallet_view, name='fund_advertiser_wallet'),
    path('analytics/', views.analytics_dashboard_view, name='analytics_dashboard'),
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
]
