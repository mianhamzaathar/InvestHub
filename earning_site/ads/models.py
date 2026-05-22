from django.db import models
from django.conf import settings
from plans.models import Plan

class Ad(models.Model):
    """
    Ad model for storing one ad per plan per day.
    Users can watch the ad to earn daily income from active plans.
    """
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='ads')
    title = models.CharField(max_length=100)
    video_url = models.URLField(help_text="YouTube embed link or video CDN URL")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.plan.name})"

class AdWatchLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    date_watched = models.DateField(auto_now_add=True)

