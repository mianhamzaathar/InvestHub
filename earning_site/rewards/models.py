from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


class EarningTask(models.Model):
    TASK_TYPES = (
        ('login_bonus', 'Daily Login Bonus'),
        ('ad', 'Watch Ad'),
        ('survey', 'Survey'),
        ('offerwall', 'Offerwall'),
        ('app_install', 'App Install'),
        ('referral', 'Referral Task'),
    )

    title = models.CharField(max_length=120)
    task_type = models.CharField(max_length=30, choices=TASK_TYPES)
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    instructions = models.TextField(blank=True)
    external_url = models.URLField(blank=True)
    daily_limit = models.PositiveIntegerField(default=1)
    duration_seconds = models.PositiveIntegerField(default=0)
    requires_review = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TaskCompletion(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='task_completions')
    task = models.ForeignKey(EarningTask, on_delete=models.CASCADE, related_name='completions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    reward_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    proof = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    device_key = models.CharField(max_length=128, blank=True)
    timer_seconds = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.user} - {self.task}"


class ReferralProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_profile')
    code = models.CharField(max_length=20, unique=True)
    referred_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='direct_referrals',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} ({self.code})"


class ReferralCommission(models.Model):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_commissions')
    referred_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generated_commissions')
    level = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class MembershipPlan(models.Model):
    name = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField(default=30)
    daily_bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    task_multiplier = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'))
    max_daily_tasks = models.PositiveIntegerField(default=5)
    faster_withdrawals = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserMembership(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='membership')
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT)
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_active(self):
        return not self.expires_at or self.expires_at >= timezone.now()

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"


class FraudSignal(models.Model):
    SEVERITY = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fraud_signals')
    signal_type = models.CharField(max_length=60)
    severity = models.CharField(max_length=10, choices=SEVERITY, default='low')
    details = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_key = models.CharField(max_length=128, blank=True)
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class DailyStreak(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_streak')
    current_streak = models.PositiveIntegerField(default=0)
    best_streak = models.PositiveIntegerField(default=0)
    last_claimed = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}: {self.current_streak}"


class SpinReward(models.Model):
    label = models.CharField(max_length=80)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    weight = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class SpinLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='spin_logs')
    reward = models.ForeignKey(SpinReward, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    spun_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-spun_at']


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=120)
    message = models.TextField()
    level = models.CharField(max_length=20, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    target = models.CharField(max_length=120, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class IntegrationProvider(models.Model):
    PROVIDER_TYPES = (
        ('payment', 'Payment'),
        ('offerwall', 'Offerwall'),
        ('ads', 'Ads'),
        ('fraud', 'Fraud Detection'),
    )

    name = models.CharField(max_length=80)
    provider_type = models.CharField(max_length=20, choices=PROVIDER_TYPES)
    public_key = models.CharField(max_length=255, blank=True)
    webhook_secret = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=False)
    sandbox_mode = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class AdvertiserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='advertiser_profile')
    company_name = models.CharField(max_length=120)
    contact_email = models.EmailField()
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name

    def debit(self, amount):
        if self.balance < amount:
            raise ValueError('Insufficient advertiser balance')
        self.balance -= amount
        self.save(update_fields=['balance'])

    def credit(self, amount):
        self.balance += amount
        self.save(update_fields=['balance'])


class Campaign(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('review', 'In Review'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    )

    advertiser = models.ForeignKey(AdvertiserProfile, on_delete=models.CASCADE, related_name='campaigns')
    title = models.CharField(max_length=140)
    description = models.TextField()
    target_url = models.URLField()
    budget = models.DecimalField(max_digits=10, decimal_places=2)
    spent_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reward_per_action = models.DecimalField(max_digits=10, decimal_places=2)
    max_actions = models.PositiveIntegerField(default=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    @property
    def remaining_budget(self):
        return max(self.budget - self.spent_amount, Decimal('0'))

    def can_charge_action(self):
        return (
            self.status == 'active'
            and self.remaining_budget >= self.reward_per_action
            and self.actions.count() < self.max_actions
        )


class CampaignAction(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='actions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='campaign_actions')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_key = models.CharField(max_length=128, blank=True)
    payout_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class AdvertiserInvoice(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    )

    advertiser = models.ForeignKey(AdvertiserProfile, on_delete=models.CASCADE, related_name='invoices')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='issued')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class DeviceToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=40, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.platform or 'device'}"
