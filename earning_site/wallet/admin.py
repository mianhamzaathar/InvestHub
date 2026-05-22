from django.contrib import admin
from .models import Wallet, WalletTransaction, WithdrawalOTP, WithdrawalRequest

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance']  # ✅ Removed created_at, updated_at
    readonly_fields = []                # ✅ No readonly fields now
    search_fields = ['user__username', 'user__email']
    list_filter = []                    # ✅ Removed created_at from list_filter

@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'transaction_type', 'source', 'amount', 'description', 'created_at']
    list_filter = ['transaction_type', 'source', 'created_at']
    search_fields = ['wallet__user__username', 'description']
    readonly_fields = ['created_at']

@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ['wallet', 'amount', 'method', 'account_number', 'status', 'created_at', 'processed_at']
    list_filter = ['status', 'method', 'created_at']
    search_fields = ['wallet__user__username']
    readonly_fields = ['created_at', 'processed_at']
    actions = ['approve_requests', 'reject_requests']

    def approve_requests(self, request, queryset):
        for withdrawal in queryset:
            withdrawal.approve()
    approve_requests.short_description = "Mark selected as approved"

    def reject_requests(self, request, queryset):
        for withdrawal in queryset:
            withdrawal.reject()
    reject_requests.short_description = "Mark selected as rejected"


@admin.register(WithdrawalOTP)
class WithdrawalOTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'is_used', 'created_at']
    list_filter = ['is_used', 'created_at']
    search_fields = ['user__username']
