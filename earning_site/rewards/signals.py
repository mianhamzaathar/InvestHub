from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DailyStreak, MembershipPlan, UserMembership
from .utils import get_or_create_referral_profile


User = get_user_model()


@receiver(post_save, sender=User)
def create_rewards_profile(sender, instance, created, **kwargs):
    if not created:
        return
    get_or_create_referral_profile(instance)
    DailyStreak.objects.get_or_create(user=instance)
    default_plan = MembershipPlan.objects.filter(is_default=True, is_active=True).first()
    if default_plan:
        UserMembership.objects.get_or_create(user=instance, defaults={'plan': default_plan})
