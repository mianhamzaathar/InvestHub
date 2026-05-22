try:
    from celery import shared_task
except Exception:
    def shared_task(func=None, **_kwargs):
        def decorator(inner):
            return inner
        return decorator(func) if func else decorator

from datetime import timedelta

from django.utils import timezone
from django.db.models import Count

from wallet.models import WithdrawalRequest
from .models import FraudSignal, Notification, TaskCompletion


@shared_task
def scan_fraud_velocity():
    flagged = 0
    one_hour_ago = timezone.now() - timedelta(hours=1)
    suspicious = (
        TaskCompletion.objects.filter(completed_at__gte=one_hour_ago)
        .values('user')
        .annotate(total=Count('id'))
        .filter(total__gte=20)
    )
    for item in suspicious:
        FraudSignal.objects.get_or_create(
            user_id=item['user'],
            signal_type='scheduled_velocity_scan',
            severity='high',
            resolved=False,
            defaults={'details': f"{item['total']} task completions in one hour."},
        )
        flagged += 1
    return {'flagged': flagged, 'ran_at': timezone.now().isoformat()}


@shared_task
def process_withdrawal_queue():
    pending = WithdrawalRequest.objects.filter(status='pending').count()
    return {'pending': pending}


@shared_task
def send_notification(user_id, title, message, level='info'):
    Notification.objects.create(user_id=user_id, title=title, message=message, level=level)
    return True
