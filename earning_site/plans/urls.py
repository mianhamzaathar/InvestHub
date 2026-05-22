from django.urls import path
from . import views

app_name = 'plans'

urlpatterns = [
    # Public main plan listing
    path('', views.plans_view, name='plans'),  # ← this is the URL `{% url 'plans:plans' %}`

    # Dashboard inside plans (optional)
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Plan actions
    path('activate/<int:plan_id>/', views.activate_plan, name='activate_plan'),
    path('upgrade/<int:plan_id>/', views.upgrade_plan_view, name='upgrade_plan'),
    path('extend/<int:plan_id>/', views.extend_plan_view, name='extend_plan'),
    path('add/', views.add_plan_view, name='add_plan'),

    # AJAX endpoints
    path('initiate-payment-ajax/', views.initiate_payment_ajax, name='initiate_payment_ajax'),
    path('verify-otp-ajax/', views.verify_otp_ajax, name='verify_otp_ajax'),
]
