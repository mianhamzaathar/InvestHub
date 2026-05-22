import random
import hashlib
import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings

from plans.models import Plan, UserPlan
from payments.models import GatewayTransaction, PaymentLog, OTPVerification
from payments.gateways import gateway_configured, gateway_mode, jazzcash_payload
from .forms import OTPForm
from django.utils import timezone

# 🔐 Generate OTP
def generate_otp():
    return str(random.randint(100000, 999999))

from twilio.rest import Client

def send_sms(phone, otp):
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f"Your OTP for InvestHub is: {otp}",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone  # Make sure it's in international format e.g., +923001234567
    )
    print(f"[DEBUG] Twilio SMS SID: {message.sid}")

# ✅ Check expired plans
def check_expired_plans(user):
    for plan in UserPlan.objects.filter(user=user, is_active=True):
        if plan.is_expired():
            plan.is_active = False
            plan.save()

# 📊 Dashboard
@login_required
def dashboard_view(request):
    check_expired_plans(request.user)
    user_plan = UserPlan.objects.filter(user=request.user, is_active=True).first()
    days_left = user_plan.days_left() if user_plan else 0
    return render(request, 'dashboard.html', {'user_plan': user_plan, 'days_left': days_left})

# 🧾 Step 1: Show plan info
@login_required
def initiate_payment_view(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    return render(request, 'initiate_payment.html', {'plan': plan})

# 💸 Step 2: Request payment, send OTP
@login_required
def request_payment(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)

    if request.method == 'POST':
        method = request.POST.get('method')
        phone = request.POST.get('phone')

        otp_code = generate_otp()

        payment_log = PaymentLog.objects.create(
            user=request.user,
            plan=plan,
            amount=plan.price,
            phone_number=phone,
            method=method,
            status='Pending'
        )

        OTPVerification.objects.create(
            user=request.user,
            payment_log=payment_log,
            phone_number=phone,
            otp_code=otp_code
        )

        send_sms(phone, otp_code)

        return redirect('payments:verify_otp_view', payment_id=payment_log.id)

    return render(request, 'payments/request_payment.html', {'plan': plan})

# 💳 Step 3: JazzCash Redirect
@login_required
def jazzcash_payment_view(request, payment_id):
    payment = get_object_or_404(PaymentLog, id=payment_id, user=request.user)

    txn_ref = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    amount = int(float(payment.amount) * 100)

    post_data = {
        "pp_Version": "1.1",
        "pp_TxnType": "MWALLET",
        "pp_Language": "EN",
        "pp_MerchantID": settings.JAZZCASH_MERCHANT_ID,
        "pp_SubMerchantID": "",
        "pp_Password": settings.JAZZCASH_PASSWORD,
        "pp_TxnRefNo": txn_ref,
        "pp_Amount": str(amount),
        "pp_TxnCurrency": "PKR",
        "pp_TxnDateTime": txn_ref,
        "pp_BillReference": f"INV-{txn_ref}",
        "pp_Description": f"Activation for {payment.plan.name}",
        "pp_ReturnURL": request.build_absolute_uri(reverse('payments:verify_otp_view', args=[payment.id])),
        "pp_SecureHash": "",
    }

    hash_string = settings.JAZZCASH_SALT + '&' + '&'.join(
        post_data[k] for k in post_data if k != 'pp_SecureHash'
    )
    post_data["pp_SecureHash"] = hashlib.sha256(hash_string.encode()).hexdigest()

    return render(request, 'payments/redirect_to_jazzcash.html', {'post_data': post_data})

# ✅ Step 4: OTP Verify and Activate Plan
@login_required
def verify_otp_view(request, payment_id):
    payment = get_object_or_404(PaymentLog, id=payment_id, user=request.user)
    otp_obj = OTPVerification.objects.filter(payment_log=payment, user=request.user, is_verified=False).first()

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')

        if otp_obj and otp_obj.otp_code == entered_otp and not otp_obj.is_expired():
            otp_obj.is_verified = True
            otp_obj.save()

            payment.status = 'Success'
            payment.save()

            UserPlan.objects.create(
                user=request.user,
                plan=payment.plan,
                is_active=True,
                activated_on=timezone.now()
            )

            messages.success(request, f"🎉 Plan '{payment.plan.name}' activated successfully!")
            return redirect('dashboard')

        messages.error(request, "❌ Invalid OTP or already used.")

    form = OTPForm()
    return render(request, 'payments/verify_otp.html', {'form': form, 'payment': payment})

# 🔐 API: Send OTP only
@csrf_exempt
@require_POST
def send_otp(request):
    phone = request.POST.get('phone')
    if not phone:
        return JsonResponse({'status': 'error', 'message': 'Phone number required'})

    otp = generate_otp()
    send_sms(phone, otp)
    return JsonResponse({'status': 'success', 'message': 'OTP sent'})

# 🪄 AJAX: Initiate Payment
@login_required
def initiate_payment_ajax(request):
    if request.method == 'POST':
        method = request.POST.get('method')
        phone = request.POST.get('phone')
        plan_id = request.POST.get('plan_id')
        plan = get_object_or_404(Plan, id=plan_id)

        otp_code = generate_otp()

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

        send_sms(phone, otp_code)
        return JsonResponse({'status': 'otp_sent'})
    return JsonResponse({'status': 'fail'})

# 🪄 AJAX: Verify OTP
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
# payments/views.py

from django.shortcuts import render, redirect
from plans.models import Plan

def activate_plan_request(request):
    if request.method == 'POST':
        plan_id = request.POST.get('plan_id')
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return redirect('plans:plans')

        return redirect('payments:initiate_payment', plan_id=plan.id)

    return redirect('plans:plans')
from django.shortcuts import render, get_object_or_404
from plans.models import Plan
from .forms import PaymentForm

def initiate_payment_view(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            # Handle OTP and Payment Logic
            ...
    else:
        form = PaymentForm()

    return render(request, 'payments/initiate_payment.html', {
        'form': form,
        'plan': plan
    })
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import PaymentForm
from plans.models import Plan

@login_required
def initiate_payment_view(request, plan_id):
    plan = get_object_or_404(Plan, id=plan_id)

    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone']
            method = form.cleaned_data['method']

            otp_code = generate_otp()
            payment_log = PaymentLog.objects.create(
                user=request.user,
                plan=plan,
                amount=plan.price,
                method=method,
                phone_number=phone,
                status='Pending',
            )
            gateway = 'ManualOTP'
            gateway_payload = {}
            if method == 'JazzCash' and gateway_mode() == 'live' and gateway_configured('JazzCash'):
                gateway = 'JazzCash'
                gateway_payload = jazzcash_payload(
                    payment_log,
                    request.build_absolute_uri(reverse('payments:verify_otp_view', args=[payment_log.id])),
                )
            elif method == 'EasyPaisa' and gateway_mode() == 'live' and gateway_configured('EasyPaisa'):
                gateway = 'EasyPaisa'
                gateway_payload = {'status': 'configured', 'note': 'Easypaisa API credentials available; implement provider request here.'}

            GatewayTransaction.objects.create(
                payment_log=payment_log,
                gateway=gateway,
                gateway_reference=payment_log.transaction_id or '',
                request_payload=gateway_payload,
            )
            OTPVerification.objects.create(
                user=request.user,
                payment_log=payment_log,
                phone_number=phone,
                otp_code=otp_code,
            )

            print(f"[DEBUG] OTP for {phone}: {otp_code}")
            messages.success(request, f"OTP sent successfully. Development OTP: {otp_code}")
            return redirect('payments:verify_otp_view', payment_id=payment_log.id)
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PaymentForm()

    return render(request, 'payments/initiate_payment.html', {
        'plan': plan,
        'form': form
    })
from twilio.rest import Client
from django.conf import settings

def send_sms(phone, otp):
    # Convert local number to international (Pakistani) format if needed
    if phone.startswith('03') and len(phone) == 11:
        phone = '+92' + phone[1:]

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    message = client.messages.create(
        body=f"Your OTP for InvestHub is: {otp}",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone
    )
    print(f"[DEBUG] Twilio SMS SID: {message.sid}")
