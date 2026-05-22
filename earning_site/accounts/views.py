from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from decimal import Decimal

from .models import CustomUser
from plans.models import Plan, UserPlan
from wallet.models import Wallet
from rewards.models import ReferralProfile
from rewards.utils import get_or_create_referral_profile


def landing_view(request):
    return render(request, 'landing.html')


def register_view(request):
    """
    Handle user registration
    """
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        pass1 = request.POST.get('password1', '')
        pass2 = request.POST.get('password2', '')
        
        print(f"Registration attempt - Username: {username}, Phone: {phone}")
        
        # Basic validation
        if not username or not phone or not pass1 or not pass2:
            messages.error(request, "❌ All fields are required.")
            return render(request, 'register.html')
        
        if pass1 != pass2:
            messages.error(request, "❌ Passwords do not match.")
            return render(request, 'register.html')
        
        if len(pass1) < 6:
            messages.error(request, "❌ Password must be at least 6 characters.")
            return render(request, 'register.html')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "❌ Username already exists.")
            return render(request, 'register.html')
        
        ref_code = request.GET.get('ref') or request.POST.get('ref_code')

        # Create user
        try:
            user = CustomUser.objects.create_user(
                username=username, 
                phone_number=phone, 
                password=pass1
            )
            print(f"User created: {user.username}")
            
            # The post-save signal also creates this; get_or_create keeps registration safe.
            Wallet.objects.get_or_create(user=user, defaults={'balance': 0})
            print("Wallet created")

            profile = get_or_create_referral_profile(user)
            if ref_code:
                referrer_profile = ReferralProfile.objects.filter(code=ref_code).select_related('user').first()
                if referrer_profile and referrer_profile.user != user:
                    profile.referred_by = referrer_profile.user
                    profile.save(update_fields=['referred_by'])
            
            messages.success(request, "✅ Account created successfully! Please log in.")
            return redirect('login')
            
        except IntegrityError as e:
            messages.error(request, f"❌ Phone number already exists.")
            return render(request, 'register.html')
        except Exception as e:
            messages.error(request, f"❌ Registration failed: {str(e)}")
            return render(request, 'register.html')
    
    return render(request, 'register.html', {'ref_code': request.GET.get('ref', '')})


def login_view(request):
    """
    Handle user login
    """
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        print(f"Login attempt - Username: {username}")
        
        # Validate inputs
        if not username or not password:
            messages.error(request, '❌ Please enter both username and password.')
            return render(request, 'login.html')
        
        # Try to authenticate
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            print(f"Login successful for user: {user.username}")
            messages.success(request, f'✅ Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            print(f"Login failed for username: {username}")
            
            # Check if username exists
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, '❌ Invalid password.')
            else:
                messages.error(request, '❌ User does not exist.')
    
    return render(request, 'login.html')


def logout_view(request):
    """
    Handle user logout
    """
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "👋 You have been logged out successfully.")
    return redirect('login')


@login_required
def dashboard_view(request):
    """
    User dashboard view
    """
    try:
        # Get active plans
        active_plans = UserPlan.objects.filter(user=request.user, is_active=True)
        
        # Get or create wallet
        try:
            wallet = Wallet.objects.get(user=request.user)
        except Wallet.DoesNotExist:
            wallet = Wallet.objects.create(user=request.user, balance=0)
        
        # Calculate daily earnings from active plans
        daily_earnings = Decimal('0')
        for plan in active_plans:
            daily_earnings += plan.plan.daily_earning if hasattr(plan, 'plan') and hasattr(plan.plan, 'daily_earning') else 0

        # Calculate total invested
        total_invested = Decimal('0')
        for plan in active_plans:
            total_invested += plan.plan.price if hasattr(plan, 'plan') and hasattr(plan.plan, 'price') else 0
        
        # Get all user plans for history
        all_plans = UserPlan.objects.filter(user=request.user)
        
        # Prepare context
        context = {
            'plans': all_plans,
            'active_plans': active_plans,
            'wallet': wallet,
            'daily_earnings': daily_earnings,
            'total_invested': total_invested,
            'active_plans_count': active_plans.count(),
            'total_plans_count': all_plans.count(),
        }
        
        # Add user_plan if there's an active plan
        if active_plans.exists():
            user_plan = active_plans.first()
            context['user_plan'] = user_plan
            context['progress_percentage'] = user_plan.progress_percentage
        
        return render(request, 'dashboard.html', context)
        
    except Exception as e:
        print(f"Dashboard error: {str(e)}")
        messages.error(request, f"❌ Error loading dashboard: {str(e)}")
        return render(request, 'dashboard.html')
    # views.py
from django.contrib.auth import get_user_model

User = get_user_model()

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        username_or_phone = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username_or_phone or not password:
            messages.error(request, '❌ Please enter both username and password.')
            return render(request, 'login.html')
        
        # Try username first
        user = authenticate(request, username=username_or_phone, password=password)
        
        # If failed, try phone number
        if user is None:
            try:
                user_obj = User.objects.get(phone_number=username_or_phone)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            login(request, user)
            messages.success(request, f'✅ Welcome back, {user.username}!')
            return redirect('dashboard')
        else:
            messages.error(request, '❌ Invalid username/phone or password.')
    
    return render(request, 'login.html')
