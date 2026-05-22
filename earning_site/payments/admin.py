# payments/admin.py
from django.contrib import admin
from .models import GatewayTransaction, OTPVerification, PaymentLog, Wallet


@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'otp_code', 'is_verified', 'created_at']
    search_fields = ['user__username', 'phone_number', 'otp_code']
    list_filter = ['is_verified', 'created_at']


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'plan', 'amount', 'method', 'status', 'created_at']
    search_fields = ['user__username', 'phone_number', 'transaction_id']
    list_filter = ['method', 'status', 'created_at']


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance']
    search_fields = ['user__username']


@admin.register(GatewayTransaction)
class GatewayTransactionAdmin(admin.ModelAdmin):
    list_display = ['payment_log', 'gateway', 'gateway_reference', 'status', 'created_at', 'updated_at']
    list_filter = ['gateway', 'status', 'created_at']
    search_fields = ['payment_log__user__username', 'gateway_reference']
