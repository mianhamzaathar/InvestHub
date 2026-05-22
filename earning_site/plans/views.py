import random
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .forms import PlanForm

from plans.models import Plan, UserPlan
from payments.models import PaymentLog, OTPVerification, Wallet
from .forms import PaymentForm, OTPForm

# 🔹 View available 
@login_required
def plans_view(request):
    plans = Plan.objects.all()
    return render(request, 'plans.html', {'plans': plans})

# 📊 Dashboard
@login_required
def dashboard_view(request):
    check_expired_plans(request.user)
    user_plan = UserPlan.objects.filter(user=request.user, is_active=True).first()
    days_left = user_plan.days_left() if user_plan else 0
    return render(request, 'dashboard.html', {'user_plan': user_plan, 'days_left': days_left})

# ✅ Activate plan manually
@login_required
def activate_plan(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)

    # Deactivate old plans
    UserPlan.objects.filter(user=request.user, is_active=True).update(is_active=False)

    # Activate new plan
    user_plan, _ = UserPlan.objects.get_or_create(user=request.user, plan=plan)
    user_plan.is_active = True
    user_plan.activated_on = timezone.now()
    user_plan.save()

    messages.success(request, f"{plan.name} plan activated.")
    return redirect('dashboard')

# 🔁 Upgrade plan (reuse activate logic)
@login_required
def upgrade_plan_view(request, plan_id):
    return activate_plan(request, plan_id)

# 🔄 Extend current plan
@login_required
def extend_plan_view(request, plan_id):
    user_plan = UserPlan.objects.filter(user=request.user, plan_id=plan_id, is_active=True).first()

    if user_plan:
        current_expiry = user_plan.activated_on + timezone.timedelta(days=user_plan.plan.duration_days)
        user_plan.activated_on = current_expiry
        user_plan.save()
        messages.success(request, f"{user_plan.plan.name} plan extended.")
    else:
        messages.warning(request, "No active plan to extend.")

    return redirect('dashboard')

# ⏳ Deactivate expired plans
def check_expired_plans(user):
    for plan in UserPlan.objects.filter(user=user, is_active=True):
        if plan.is_expired():
            plan.is_active = False
            plan.save()

# 🪄 AJAX: Initiate payment & OTP
@login_required
def initiate_payment_ajax(request):
    if request.method == 'POST':
        method = request.POST.get('method')
        phone = request.POST.get('phone')
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(Plan, id=plan_id)

        otp_code = get_random_string(6, allowed_chars='0123456789')

        payment_log = PaymentLog.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            method=method,
            phone_number=phone,
            status="Pending"
        )

        OTPVerification.objects.create(
            user=request.user,
            payment_log=payment_log,
            phone_number=phone,
            otp_code=otp_code,
        )

        print(f"[DEBUG] OTP sent: {otp_code}")
        return JsonResponse({'status': 'otp_sent'})

    return JsonResponse({'status': 'fail'})

# ✅ AJAX: Verify OTP
@login_required
def verify_otp_ajax(request):
    if request.method == 'POST':
        otp = request.POST.get('otp')
        plan_id = request.POST.get('plan_id')

        try:
            plan = Plan.objects.get(id=plan_id)
            otp_obj = OTPVerification.objects.filter(user=request.user, otp_code=otp, is_verified=False).latest('created_at')

            if otp_obj.is_expired():
                return JsonResponse({'status': 'expired'})

            otp_obj.is_verified = True
            otp_obj.save()

            otp_obj.payment_log.status = 'Success'
            otp_obj.payment_log.save()

            UserPlan.objects.create(
                user=request.user,
                plan=plan,
                is_active=True,
                activated_on=timezone.now()
            )

            return JsonResponse({'status': 'plan_activated'})

        except OTPVerification.DoesNotExist:
            return JsonResponse({'status': 'invalid'})

    return JsonResponse({'status': 'fail'})
@login_required
def add_plan_view(request):
    if request.method == 'POST':
        form = PlanForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Plan added successfully.")
            return redirect('plans:plans_view')
    else:
        form = PlanForm()
    return render(request, 'add_plan.html', {'form': form})
# plans/views.py
from django.shortcuts import render

def plan_list(request):
    return render(request, 'plans/plan_list.html')  # Adjust template path as needed
from payments.models import Wallet

@login_required
def plans_view(request):
    plans = Plan.objects.all()
    wallet = Wallet.objects.filter(user=request.user).first()
    return render(request, 'plans.html', {
        'plans': plans,
        'wallet': wallet
    })
