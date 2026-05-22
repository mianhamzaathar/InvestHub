from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from decimal import Decimal, InvalidOperation
import random

from wallet.models import Wallet, WithdrawalOTP, WithdrawalRequest

@login_required
def withdraw_view(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()
        latest_otp = WithdrawalOTP.objects.filter(user=request.user, is_used=False).order_by('-created_at').first()
        if not latest_otp or latest_otp.is_expired() or latest_otp.code != otp_code:
            code = str(random.randint(100000, 999999))
            WithdrawalOTP.objects.create(user=request.user, code=code)
            messages.info(request, f'Withdrawal OTP generated. Development OTP: {code}')
            return redirect('withdraw')
        try:
            amount = Decimal(request.POST.get('amount', '0'))
        except (InvalidOperation, TypeError):
            amount = Decimal('0')
        if amount <= 0:
            messages.error(request, 'Enter a valid withdrawal amount.')
        elif wallet.balance < amount:
            messages.error(request, 'Insufficient balance.')
        else:
            latest_otp.is_used = True
            latest_otp.save(update_fields=['is_used'])
            wallet.debit(amount, source='withdrawal', description='Withdrawal request submitted')
            WithdrawalRequest.objects.create(
                wallet=wallet,
                amount=amount,
                method=request.POST.get('method', 'JazzCash'),
                account_number=request.POST.get('account_number', ''),
                account_title=request.POST.get('account_title', ''),
            )
            messages.success(request, 'Withdrawal request submitted for admin review.')
            return redirect('withdraw')
    return render(request, 'withdraw.html', {
        'wallet': wallet,
        'withdrawals': WithdrawalRequest.objects.filter(wallet=wallet).order_by('-created_at'),
        'transactions': wallet.transactions.all()[:20],
    })
