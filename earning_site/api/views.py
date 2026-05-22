from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from rewards.models import DeviceToken, EarningTask, Notification, TaskCompletion
from wallet.models import Wallet, WithdrawalRequest


def serialize_task(task):
    return {
        'id': task.id,
        'title': task.title,
        'type': task.task_type,
        'reward_amount': str(task.reward_amount),
        'daily_limit': task.daily_limit,
        'duration_seconds': task.duration_seconds,
        'requires_review': task.requires_review,
    }


@login_required
@require_GET
def me(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    return JsonResponse({
        'user': {
            'id': request.user.id,
            'username': request.user.username,
            'phone_number': getattr(request.user, 'phone_number', ''),
        },
        'wallet': {'balance': str(wallet.balance)},
        'membership': getattr(getattr(request.user, 'membership', None), 'plan_id', None),
        'unread_notifications': Notification.objects.filter(user=request.user, is_read=False).count(),
    })


@login_required
@require_GET
def tasks(request):
    return JsonResponse({'tasks': [serialize_task(task) for task in EarningTask.objects.filter(is_active=True)]})


@login_required
@require_GET
def analytics(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    return JsonResponse({
        'wallet_balance': str(wallet.balance),
        'task_earnings': str(TaskCompletion.objects.filter(user=request.user, status='approved').aggregate(total=Sum('reward_amount'))['total'] or 0),
        'withdrawals_pending': WithdrawalRequest.objects.filter(wallet=wallet, status='pending').count(),
        'withdrawals_approved': str(WithdrawalRequest.objects.filter(wallet=wallet, status='approved').aggregate(total=Sum('amount'))['total'] or 0),
    })


@login_required
@require_GET
def notifications(request):
    items = Notification.objects.filter(user=request.user)[:20]
    return JsonResponse({
        'notifications': [
            {'id': n.id, 'title': n.title, 'message': n.message, 'level': n.level, 'is_read': n.is_read, 'created_at': n.created_at.isoformat()}
            for n in items
        ]
    })


@login_required
@require_POST
def register_device_token(request):
    token = request.POST.get('token', '').strip()
    platform = request.POST.get('platform', '').strip()[:40]
    if not token:
        return JsonResponse({'error': 'Device token is required.'}, status=400)
    device, created = DeviceToken.objects.update_or_create(
        token=token,
        defaults={'user': request.user, 'platform': platform, 'is_active': True},
    )
    return JsonResponse({
        'created': created,
        'device_token': {
            'id': device.id,
            'platform': device.platform,
            'is_active': device.is_active,
        },
    })
