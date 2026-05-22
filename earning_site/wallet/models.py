from datetime import timedelta

from django.db import models
from django.conf import settings
from django.utils import timezone

class WalletTransaction(models.Model):
    TYPE_CHOICES = (
        ('credit', 'Credit'),
        ('debit', 'Debit'),
    )
    SOURCE_CHOICES = (
        ('login_bonus', 'Daily Login Bonus'),
        ('task', 'Task Reward'),
        ('referral', 'Referral Commission'),
        ('spin', 'Spin Reward'),
        ('ad', 'Ad Reward'),
        ('withdrawal', 'Withdrawal'),
        ('admin', 'Admin Adjustment'),
    )

    wallet = models.ForeignKey('Wallet', on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.wallet.user.username} {self.transaction_type} {self.amount}"

class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet_wallet'  # ✅ unique
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)

    def credit(self, amount, source='admin', description=''):
        self.balance += amount
        self.save(update_fields=['balance'])
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type='credit',
            source=source,
            amount=amount,
            description=description,
        )

    def debit(self, amount, source='withdrawal', description=''):
        if self.balance < amount:
            raise ValueError('Insufficient balance')
        self.balance -= amount
        self.save(update_fields=['balance'])
        return WalletTransaction.objects.create(
            wallet=self,
            transaction_type='debit',
            source=source,
            amount=amount,
            description=description,
        )

    def __str__(self):
        return f"{self.user.username}'s Wallet"


class WithdrawalRequest(models.Model):
    METHOD_CHOICES = (
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
        ('Bank', 'Bank Transfer'),
    )

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=METHOD_CHOICES, default='JazzCash')
    account_number = models.CharField(max_length=40, blank=True)
    account_title = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')
    ), default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.wallet.user.username} - {self.amount} PKR"

    def approve(self):
        self.status = 'approved'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])

    def reject(self):
        if self.status == 'pending' and self.wallet:
            self.wallet.credit(self.amount, source='admin', description='Rejected withdrawal refund')
        self.status = 'rejected'
        self.processed_at = timezone.now()
        self.save(update_fields=['status', 'processed_at'])


class WithdrawalOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='withdrawal_otps')
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)
