from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from ads.models import Ad
from plans.models import UserPlan
from wallet.models import Wallet
from datetime import date

@login_required
def watch_ad_view(request, plan_id):
    # Get user's active plan
    user_plan = get_object_or_404(UserPlan, user=request.user, plan_id=plan_id, is_active=True)

    # Check if already watched today
    if user_plan.last_ad_watched == date.today():
        return render(request, 'watch_ad.html', {'msg': '✅ You have already watched today\'s ad for this plan.'})

    # Get the latest ad for this plan
    ad = Ad.objects.filter(plan_id=plan_id).order_by('-id').first()
    if not ad:
        return render(request, 'watch_ad.html', {'msg': '❌ No ad available for this plan today.'})

    if request.method == 'POST':
        # Mark as watched today
        user_plan.last_ad_watched = date.today()
        user_plan.save()

        # Add earnings to wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.balance += user_plan.plan.daily_earning
        wallet.save()

        return redirect('dashboard')

    return render(request, 'watch_ad.html', {'ad': ad})
# Removed stray line referencing user_plan outside of function scope

