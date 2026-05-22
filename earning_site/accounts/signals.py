from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from wallet.models import Wallet
from .models import CustomUser

@receiver(post_save, sender=CustomUser)
def create_wallet(sender, instance, created, **kwargs):
    if created:
        Wallet.objects.create(user=instance)
