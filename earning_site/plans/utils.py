from .models import UserPlan
from django.utils import timezone

def activate_plan_logic(user, plan):
    # Deactivate all existing active plans
    UserPlan.objects.filter(user=user, is_active=True).update(is_active=False)

    # Activate existing or create new
    user_plan, created = UserPlan.objects.get_or_create(user=user, plan=plan)
    user_plan.is_active = True
    user_plan.activated_on = timezone.now()
    user_plan.save()
