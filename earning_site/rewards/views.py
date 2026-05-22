import random
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from wallet.models import Wallet
from wallet.models import WithdrawalRequest
from .models import (
    AdvertiserProfile,
    AdvertiserInvoice,
    Campaign,
    CampaignAction,
    DailyStreak,
    EarningTask,
    FraudSignal,
    MembershipPlan,
    SpinLog,
    SpinReward,
    TaskCompletion,
    UserMembership,
)
from .utils import (
    award_referral_commissions,
    get_client_ip,
    get_device_key,
    get_or_create_referral_profile,
    inspect_request_for_fraud,
    record_fraud_signal,
    run_user_fraud_checks,
    today,
)


@login_required
def tasks_view(request):
    inspect_request_for_fraud(request)
    membership = getattr(request.user, 'membership', None)
    tasks = EarningTask.objects.filter(is_active=True).order_by('task_type', 'id')
    completions_today = TaskCompletion.objects.filter(user=request.user, completed_at__date=today())
    completed_counts = completions_today.values('task_id').annotate(total=Count('id'))
    count_map = {item['task_id']: item['total'] for item in completed_counts}
    total_today = completions_today.filter(status='approved').aggregate(total=Sum('reward_amount'))['total'] or Decimal('0')
    return render(request, 'rewards/tasks.html', {
        'tasks': tasks,
        'count_map': count_map,
        'membership': membership,
        'total_today': total_today,
        'completions': TaskCompletion.objects.filter(user=request.user)[:12],
    })


@login_required
def complete_task_view(request, task_id):
    task = get_object_or_404(EarningTask, id=task_id, is_active=True)
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    completed_today = TaskCompletion.objects.filter(user=request.user, task=task, completed_at__date=today()).count()
    if completed_today >= task.daily_limit:
        messages.warning(request, 'Daily limit reached for this task.')
        return redirect('rewards:tasks')

    timer_seconds = int(request.POST.get('timer_seconds', 0) or 0)
    if task.duration_seconds and timer_seconds < task.duration_seconds:
        record_fraud_signal(request.user, 'task_timer_short', 'high', f'{timer_seconds}s submitted for {task.duration_seconds}s task.', request)
        messages.error(request, 'Task timer validation failed.')
        return redirect('rewards:tasks')

    membership = getattr(request.user, 'membership', None)
    multiplier = membership.plan.task_multiplier if membership and membership.is_active else Decimal('1.00')
    reward = (task.reward_amount * multiplier).quantize(Decimal('0.01'))
    status = 'pending' if task.requires_review else 'approved'
    TaskCompletion.objects.create(
        user=request.user,
        task=task,
        status=status,
        reward_amount=reward,
        proof=request.POST.get('proof', ''),
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        device_key=get_device_key(request),
        timer_seconds=timer_seconds,
    )
    run_user_fraud_checks(request.user, request)
    if status == 'approved':
        wallet.credit(reward, source='task', description=task.title)
        award_referral_commissions(request.user, reward, f'Task reward: {task.title}')
        messages.success(request, f'Task completed. Rs. {reward} added to wallet.')
    else:
        messages.info(request, 'Task submitted for admin review.')
    return redirect('rewards:tasks')


@login_required
def claim_login_bonus_view(request):
    streak, _ = DailyStreak.objects.get_or_create(user=request.user)
    if streak.last_claimed == today():
        messages.info(request, 'Daily login bonus already claimed today.')
        return redirect('rewards:tasks')

    yesterday = today() - timedelta(days=1)
    streak.current_streak = streak.current_streak + 1 if streak.last_claimed == yesterday else 1
    streak.best_streak = max(streak.best_streak, streak.current_streak)
    streak.last_claimed = today()
    streak.save()

    membership = getattr(request.user, 'membership', None)
    amount = membership.plan.daily_bonus if membership and membership.is_active else Decimal('5.00')
    bonus = amount + Decimal(min(streak.current_streak, 10))
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    wallet.credit(bonus, source='login_bonus', description=f'{streak.current_streak}-day streak bonus')
    award_referral_commissions(request.user, bonus, 'Daily login bonus')
    messages.success(request, f'Daily bonus claimed: Rs. {bonus}')
    return redirect('rewards:tasks')


@login_required
def referral_view(request):
    profile = get_or_create_referral_profile(request.user)
    invite_url = request.build_absolute_uri(reverse('register')) + f'?ref={profile.code}'
    commission_qs = request.user.referral_commissions.all()
    commissions = commission_qs[:20]
    return render(request, 'rewards/referrals.html', {
        'profile': profile,
        'invite_url': invite_url,
        'direct_referrals': request.user.direct_referrals.all(),
        'commissions': commissions,
        'total_commission': commission_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0'),
    })


@login_required
def membership_view(request):
    plans = MembershipPlan.objects.filter(is_active=True).order_by('price')
    current = getattr(request.user, 'membership', None)
    if request.method == 'POST':
        plan = get_object_or_404(MembershipPlan, id=request.POST.get('plan_id'), is_active=True)
        membership, _ = UserMembership.objects.get_or_create(user=request.user, defaults={'plan': plan})
        membership.plan = plan
        membership.started_at = timezone.now()
        membership.expires_at = timezone.now() + timedelta(days=plan.duration_days)
        membership.save()
        messages.success(request, f'{plan.name} membership activated.')
        return redirect('rewards:membership')
    return render(request, 'rewards/membership.html', {'plans': plans, 'current': current})


@login_required
def spin_view(request):
    rewards = list(SpinReward.objects.filter(is_active=True))
    logs = SpinLog.objects.filter(user=request.user)[:10]
    if request.method == 'POST':
        if SpinLog.objects.filter(user=request.user, spun_at__date=today()).exists():
            messages.warning(request, 'You have already used today’s spin.')
            return redirect('rewards:spin')
        if not rewards:
            messages.error(request, 'No spin rewards configured by admin.')
            return redirect('rewards:spin')
        reward = random.choices(rewards, weights=[r.weight for r in rewards], k=1)[0]
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.credit(reward.amount, source='spin', description=reward.label)
        SpinLog.objects.create(user=request.user, reward=reward, amount=reward.amount)
        messages.success(request, f'Spin reward won: {reward.label}')
        return redirect('rewards:spin')
    return render(request, 'rewards/spin.html', {'rewards': rewards, 'logs': logs})


def legal_page(request, page):
    titles = {
        'terms': 'Terms of Service',
        'privacy': 'Privacy Policy',
        'earning-rules': 'Earning Rules',
        'withdrawal-proof': 'Withdrawal Proof & Transparency',
    }
    return render(request, 'rewards/legal.html', {'page': page, 'title': titles.get(page, 'Legal')})


def manifest_view(request):
    return JsonResponse({
        'name': 'InvestHub',
        'short_name': 'InvestHub',
        'start_url': '/login/',
        'display': 'standalone',
        'background_color': '#fbfaf5',
        'theme_color': '#2a3048',
        'description': 'InvestHub smart earning dashboard',
    })


def service_worker_view(request):
    js = """
self.addEventListener('install', event => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {});
"""
    return HttpResponse(js, content_type='application/javascript')


@staff_member_required
def admin_analytics_view(request):
    return render(request, 'rewards/admin_analytics.html', {
        'total_wallet_balance': Wallet.objects.aggregate(total=Sum('balance'))['total'] or Decimal('0'),
        'pending_withdrawals': WithdrawalRequest.objects.filter(status='pending').count(),
        'approved_withdrawals': WithdrawalRequest.objects.filter(status='approved').aggregate(total=Sum('amount'))['total'] or Decimal('0'),
        'task_completions': TaskCompletion.objects.count(),
        'pending_tasks': TaskCompletion.objects.filter(status='pending').count(),
        'fraud_high': FraudSignal.objects.filter(severity='high', resolved=False).count(),
        'recent_fraud': FraudSignal.objects.filter(resolved=False)[:10],
        'top_tasks': EarningTask.objects.annotate(total=Count('completions')).order_by('-total')[:10],
    })


@login_required
def advertiser_panel_view(request):
    profile = getattr(request.user, 'advertiser_profile', None)
    if request.method == 'POST' and not profile:
        profile = AdvertiserProfile.objects.create(
            user=request.user,
            company_name=request.POST.get('company_name', ''),
            contact_email=request.POST.get('contact_email', request.user.email or ''),
        )
        messages.success(request, 'Advertiser profile submitted for admin approval.')
        return redirect('rewards:advertiser_panel')
    campaigns = profile.campaigns.all() if profile else []
    return render(request, 'rewards/advertiser_panel.html', {'profile': profile, 'campaigns': campaigns})


@login_required
def create_campaign_view(request):
    profile = getattr(request.user, 'advertiser_profile', None)
    if not profile or not profile.is_approved:
        messages.error(request, 'Advertiser profile must be approved before creating campaigns.')
        return redirect('rewards:advertiser_panel')
    if request.method == 'POST':
        budget = Decimal(request.POST.get('budget', '0') or '0')
        reward_per_action = Decimal(request.POST.get('reward_per_action', '0') or '0')
        if budget <= 0 or reward_per_action <= 0:
            messages.error(request, 'Campaign budget and reward per action must be greater than zero.')
            return redirect('rewards:advertiser_panel')
        if profile.balance < budget:
            messages.error(request, 'Advertiser wallet balance is lower than this campaign budget.')
            return redirect('rewards:advertiser_panel')
        profile.debit(budget)
        Campaign.objects.create(
            advertiser=profile,
            title=request.POST.get('title', ''),
            description=request.POST.get('description', ''),
            target_url=request.POST.get('target_url', ''),
            budget=budget,
            reward_per_action=reward_per_action,
            max_actions=request.POST.get('max_actions', '100') or '100',
            status='review',
        )
        messages.success(request, 'Campaign submitted for admin review.')
    return redirect('rewards:advertiser_panel')


@login_required
def fund_advertiser_wallet_view(request):
    profile = getattr(request.user, 'advertiser_profile', None)
    if not profile:
        messages.error(request, 'Create an advertiser profile first.')
        return redirect('rewards:advertiser_panel')
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount', '0') or '0')
        if amount <= 0:
            messages.error(request, 'Enter a valid amount.')
        else:
            AdvertiserInvoice.objects.create(advertiser=profile, amount=amount, notes='Manual funding invoice')
            messages.success(request, 'Funding invoice created for admin/payment verification.')
    return redirect('rewards:advertiser_panel')


@staff_member_required
def analytics_dashboard_view(request):
    last_14 = []
    for days_back in range(13, -1, -1):
        day = timezone.localdate() - timedelta(days=days_back)
        last_14.append({
            'label': day.strftime('%b %d'),
            'tasks': TaskCompletion.objects.filter(completed_at__date=day).count(),
            'withdrawals': WithdrawalRequest.objects.filter(created_at__date=day).count(),
            'fraud': FraudSignal.objects.filter(created_at__date=day).count(),
        })
    return render(request, 'rewards/analytics_dashboard.html', {'series': last_14})
