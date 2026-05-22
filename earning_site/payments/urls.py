# payments/urls.py
from django.urls import path
from payments import views as payments_views

app_name = 'payments'

urlpatterns = [
    path('', payments_views.dashboard_view, name='dashboard'),

    # Plan payment flow
    path('plans/initiate/<int:plan_id>/', payments_views.initiate_payment_view, name='initiate_payment'),
    path('plans/request/<int:plan_id>/', payments_views.request_payment, name='request_payment'),
    path('plans/verify-otp/<int:payment_id>/', payments_views.verify_otp_view, name='verify_otp_view'),
    path('jazzcash-payment/<int:payment_id>/', payments_views.jazzcash_payment_view, name='jazzcash_payment'),
    path('activate/', payments_views.activate_plan_request, name='activate_plan_request'),
path('plans/initiate/<int:plan_id>/',payments_views.initiate_payment_view, name='initiate_payment'),

    # AJAX endpoints
    path('ajax/initiate/', payments_views.initiate_payment_ajax, name='initiate_payment_ajax'),
    path('ajax/verify-otp/', payments_views.verify_otp_ajax, name='verify_otp_ajax'),


    # OTP only
    path('send-otp/', payments_views.send_otp, name='send_otp'),
]
