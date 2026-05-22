from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from accounts.views import register_view, login_view, logout_view, dashboard_view, landing_view
from rewards.views import manifest_view, service_worker_view

urlpatterns = [
    # Landing page
    path('', landing_view, name='root_redirect'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', dashboard_view, name='dashboard'),
    
    # App URLs (REMOVED DUPLICATES)
    path('plans/', include('plans.urls', namespace='plans')),
    path('payment/', include('payments.urls', namespace='payments')),
    path('ads/', include('ads.urls', namespace='ads')),
    path('rewards/', include('rewards.urls', namespace='rewards')),
    path('wallet/', include('wallet.urls')),
    path('api/v1/', include('api.urls', namespace='api')),
    path('manifest.json', manifest_view, name='manifest'),
    path('sw.js', service_worker_view, name='service_worker'),
    
    # Password reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='registration/password_reset.html',
             email_template_name='registration/password_reset_email.html',
             subject_template_name='registration/password_reset_subject.txt'
         ), 
         name='password_reset'),
    
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='registration/password_reset_done.html'
         ), 
         name='password_reset_done'),
    
    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='registration/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    
    path('reset/done/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='registration/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
]
