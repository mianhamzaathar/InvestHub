# payments/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def __str__(self):
        return f"{self.user.username}'s Wallet"


class PaymentLog(models.Model):
    METHOD_CHOICES = (
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
    )

    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Verified', 'Verified'),
        ('Success', 'Success'),
        ('Failed', 'Failed'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_logs'
    )
    plan = models.ForeignKey(
        'plans.Plan',
        on_delete=models.CASCADE,
        related_name='payment_logs'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES)
    phone_number = models.CharField(max_length=15)
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} - {self.status}"


class OTPVerification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='otp_verifications'
    )
    payment_log = models.ForeignKey(
        PaymentLog,
        on_delete=models.CASCADE,
        related_name='otp_verifications'
    )
    phone_number = models.CharField(max_length=15)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.user.username} ({'✅' if self.is_verified else '❌'})"


class GatewayTransaction(models.Model):
    GATEWAYS = (
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
        ('Stripe', 'Stripe'),
        ('ManualOTP', 'Manual OTP'),
    )
    STATUS = (
        ('created', 'Created'),
        ('redirected', 'Redirected'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
        ('webhook_received', 'Webhook Received'),
    )

    payment_log = models.ForeignKey(PaymentLog, on_delete=models.CASCADE, related_name='gateway_transactions')
    gateway = models.CharField(max_length=30, choices=GATEWAYS)
    gateway_reference = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=30, choices=STATUS, default='created')
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.gateway} - {self.payment_log_id} - {self.status}"
