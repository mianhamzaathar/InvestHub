from django.contrib import admin
from django.db.models import Sum
from django.utils.html import format_html

from .models import (
    DailyStreak,
    EarningTask,
    FraudSignal,
    MembershipPlan,
    ReferralCommission,
    ReferralProfile,
    SpinLog,
    SpinReward,
    TaskCompletion,
    UserMembership,
    Notification,
    AuditLog,
    IntegrationProvider,
    AdvertiserProfile,
    AdvertiserInvoice,
    Campaign,
    CampaignAction,
    DeviceToken,
)


@admin.register(EarningTask)
class EarningTaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'task_type', 'reward_amount', 'daily_limit', 'duration_seconds', 'requires_review', 'is_active']
    list_filter = ['task_type', 'requires_review', 'is_active']
    search_fields = ['title']


@admin.register(TaskCompletion)
class TaskCompletionAdmin(admin.ModelAdmin):
    list_display = ['user', 'task', 'status', 'reward_amount', 'ip_address', 'timer_seconds', 'completed_at']
    list_filter = ['status', 'task__task_type', 'completed_at']
    search_fields = ['user__username', 'task__title', 'ip_address']
    actions = ['approve_selected', 'reject_selected']

    def approve_selected(self, request, queryset):
        queryset.update(status='approved')

    def reject_selected(self, request, queryset):
        queryset.update(status='rejected')


@admin.register(ReferralProfile)
class ReferralProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'referred_by', 'created_at']
    search_fields = ['user__username', 'code', 'referred_by__username']


@admin.register(ReferralCommission)
class ReferralCommissionAdmin(admin.ModelAdmin):
    list_display = ['referrer', 'referred_user', 'level', 'amount', 'created_at']
    list_filter = ['level', 'created_at']
    search_fields = ['referrer__username', 'referred_user__username']


@admin.register(MembershipPlan)
class MembershipPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_days', 'daily_bonus', 'task_multiplier', 'max_daily_tasks', 'faster_withdrawals', 'is_default', 'is_active']
    list_filter = ['is_default', 'is_active', 'faster_withdrawals']


@admin.register(UserMembership)
class UserMembershipAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'started_at', 'expires_at', 'is_active']
    search_fields = ['user__username', 'plan__name']


@admin.register(FraudSignal)
class FraudSignalAdmin(admin.ModelAdmin):
    list_display = ['user', 'signal_type', 'severity_badge', 'ip_address', 'resolved', 'created_at']
    list_filter = ['severity', 'resolved', 'signal_type', 'created_at']
    search_fields = ['user__username', 'ip_address', 'device_key']
    actions = ['mark_resolved']

    def severity_badge(self, obj):
        color = {'low': '#69a17f', 'medium': '#efbe6c', 'high': '#d36856'}.get(obj.severity, '#777')
        return format_html('<strong style="color:{}">{}</strong>', color, obj.severity.title())

    def mark_resolved(self, request, queryset):
        queryset.update(resolved=True)


@admin.register(DailyStreak)
class DailyStreakAdmin(admin.ModelAdmin):
    list_display = ['user', 'current_streak', 'best_streak', 'last_claimed']
    search_fields = ['user__username']


@admin.register(SpinReward)
class SpinRewardAdmin(admin.ModelAdmin):
    list_display = ['label', 'amount', 'weight', 'is_active']
    list_filter = ['is_active']


@admin.register(SpinLog)
class SpinLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'amount', 'spun_at']
    list_filter = ['spun_at']
    search_fields = ['user__username']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'level', 'is_read', 'created_at']
    list_filter = ['level', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['actor', 'action', 'target', 'ip_address', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['actor__username', 'action', 'target']
    readonly_fields = ['created_at']


@admin.register(IntegrationProvider)
class IntegrationProviderAdmin(admin.ModelAdmin):
    list_display = ['name', 'provider_type', 'is_active', 'sandbox_mode']
    list_filter = ['provider_type', 'is_active', 'sandbox_mode']
    search_fields = ['name']


@admin.register(AdvertiserProfile)
class AdvertiserProfileAdmin(admin.ModelAdmin):
    list_display = ['company_name', 'user', 'contact_email', 'balance', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['company_name', 'user__username', 'contact_email']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ['title', 'advertiser', 'budget', 'spent_amount', 'reward_per_action', 'max_actions', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['title', 'advertiser__company_name']


@admin.register(CampaignAction)
class CampaignActionAdmin(admin.ModelAdmin):
    list_display = ['campaign', 'user', 'payout_amount', 'is_approved', 'ip_address', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['campaign__title', 'user__username', 'ip_address', 'device_key']


@admin.register(AdvertiserInvoice)
class AdvertiserInvoiceAdmin(admin.ModelAdmin):
    list_display = ['advertiser', 'amount', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'created_at']
    search_fields = ['advertiser__company_name', 'advertiser__user__username']
    actions = ['mark_paid']

    def mark_paid(self, request, queryset):
        from django.utils import timezone

        for invoice in queryset.filter(status__in=['draft', 'issued']):
            invoice.status = 'paid'
            invoice.paid_at = timezone.now()
            invoice.save(update_fields=['status', 'paid_at'])
            invoice.advertiser.credit(invoice.amount)


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'platform', 'is_active', 'updated_at']
    list_filter = ['platform', 'is_active', 'updated_at']
    search_fields = ['user__username', 'token']
