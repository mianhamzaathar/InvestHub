import hashlib
import random
import string
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.db.models import Count, Sum

from wallet.models import Wallet
from .models import CampaignAction, FraudSignal, ReferralCommission, ReferralProfile, TaskCompletion


SUSPICIOUS_USER_AGENTS = ('vpn', 'proxy', 'tor', 'headless')


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def get_device_key(request):
    raw = '|'.join([
        request.META.get('HTTP_USER_AGENT', ''),
        request.META.get('HTTP_ACCEPT_LANGUAGE', ''),
        request.META.get('HTTP_SEC_CH_UA_PLATFORM', ''),
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:64]


def generate_referral_code(username):
    base = ''.join(ch for ch in username.upper() if ch.isalnum())[:8] or 'INVEST'
    return f"{base}{''.join(random.choices(string.digits, k=4))}"


def get_or_create_referral_profile(user):
    profile = getattr(user, 'referral_profile', None)
    if profile:
        return profile
    code = generate_referral_code(user.username)
    while ReferralProfile.objects.filter(code=code).exists():
        code = generate_referral_code(user.username)
    return ReferralProfile.objects.create(user=user, code=code)


def record_fraud_signal(user, signal_type, severity='low', details='', request=None):
    return FraudSignal.objects.create(
        user=user,
        signal_type=signal_type,
        severity=severity,
        details=details,
        ip_address=get_client_ip(request) if request else None,
        device_key=get_device_key(request) if request else '',
    )


def inspect_request_for_fraud(request):
    ua = request.META.get('HTTP_USER_AGENT', '').lower()
    if any(token in ua for token in SUSPICIOUS_USER_AGENTS):
        record_fraud_signal(
            request.user,
            'suspicious_user_agent',
            'medium',
            'User agent matched proxy/headless keywords.',
            request,
        )


def detect_user_velocity(user, request=None):
    now = timezone.now()
    one_hour_ago = now - timedelta(hours=1)
    today_start = timezone.localtime(now).replace(hour=0, minute=0, second=0, microsecond=0)

    hourly_tasks = TaskCompletion.objects.filter(user=user, completed_at__gte=one_hour_ago).count()
    if hourly_tasks >= 20:
        record_fraud_signal(user, 'rapid_task_completion', 'high', f'{hourly_tasks} tasks completed in the last hour.', request)

    daily_earnings = TaskCompletion.objects.filter(user=user, status='approved', completed_at__gte=today_start).aggregate(total=Sum('reward_amount'))['total'] or 0
    if daily_earnings and daily_earnings >= 1000:
        record_fraud_signal(user, 'earning_spike', 'medium', f'Approved task earnings today: {daily_earnings}', request)


def detect_duplicate_ip_or_device(user, request=None):
    ip = get_client_ip(request) if request else None
    device_key = get_device_key(request) if request else ''
    if ip:
        users_on_ip = TaskCompletion.objects.filter(ip_address=ip).exclude(user=user).values('user_id').distinct().count()
        if users_on_ip >= 3:
            record_fraud_signal(user, 'shared_ip_many_accounts', 'medium', f'{users_on_ip} other users have completions from this IP.', request)
    if device_key:
        users_on_device = TaskCompletion.objects.filter(device_key=device_key).exclude(user=user).values('user_id').distinct().count()
        if users_on_device >= 1:
            record_fraud_signal(user, 'shared_device_multiple_accounts', 'high', f'{users_on_device} other users share this device fingerprint.', request)


def run_user_fraud_checks(user, request=None):
    inspect_request_for_fraud(request) if request else None
    detect_user_velocity(user, request)
    detect_duplicate_ip_or_device(user, request)


def record_campaign_action(campaign, user, request=None):
    if not campaign.can_charge_action():
        return None
    existing_action = CampaignAction.objects.filter(campaign=campaign, user=user).first()
    if existing_action:
        return existing_action

    payout = campaign.reward_per_action
    action = CampaignAction.objects.create(
        campaign=campaign,
        user=user,
        ip_address=get_client_ip(request) if request else None,
        device_key=get_device_key(request) if request else '',
        payout_amount=payout,
    )
    campaign.spent_amount += payout
    if campaign.actions.count() >= campaign.max_actions or campaign.remaining_budget <= 0:
        campaign.status = 'completed'
        campaign.save(update_fields=['spent_amount', 'status'])
    else:
        campaign.save(update_fields=['spent_amount'])

    wallet, _ = Wallet.objects.get_or_create(user=user)
    wallet.credit(payout, source='task', description=f'Campaign action: {campaign.title}')
    return action


def award_referral_commissions(referred_user, base_amount, description):
    profile = getattr(referred_user, 'referral_profile', None)
    referrer = profile.referred_by if profile else None
    rates = [(1, Decimal('0.10')), (2, Decimal('0.03')), (3, Decimal('0.01'))]
    for level, rate in rates:
        if not referrer:
            break
        amount = (base_amount * rate).quantize(Decimal('0.01'))
        wallet, _ = Wallet.objects.get_or_create(user=referrer)
        wallet.credit(amount, source='referral', description=f"Level {level}: {description}")
        ReferralCommission.objects.create(
            referrer=referrer,
            referred_user=referred_user,
            level=level,
            amount=amount,
            description=description,
        )
        ref_profile = getattr(referrer, 'referral_profile', None)
        referrer = ref_profile.referred_by if ref_profile else None


def today():
    return timezone.localdate()
