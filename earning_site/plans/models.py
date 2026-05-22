# plans/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class Plan(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    daily_earning = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    roi_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    duration_days = models.PositiveIntegerField()
    is_popular = models.BooleanField(default=False)  # Used in admin

    def __str__(self):
        return self.name


class UserPlan(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='user_plans'
    )
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)
    activated_on = models.DateTimeField(null=True, blank=True)
    last_ad_watched = models.DateField(null=True, blank=True)

    def days_left(self):
        if self.activated_on:
            expiry_date = self.activated_on + timedelta(days=self.plan.duration_days)
            return max((expiry_date - timezone.now()).days, 0)
        return 0

    @property
    def end_date(self):
        if self.activated_on:
            return self.activated_on + timedelta(days=self.plan.duration_days)
        return None

    @property
    def progress_percentage(self):
        if not self.activated_on or not self.plan.duration_days:
            return 0
        elapsed_days = self.plan.duration_days - self.days_left()
        return min(max(int((elapsed_days / self.plan.duration_days) * 100), 0), 100)

    def is_expired(self):
        return self.days_left() <= 0

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
