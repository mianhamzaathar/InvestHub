# plans/admin.py
from django.contrib import admin
from .models import Plan, UserPlan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'price', 'duration_days', 'is_popular']
    search_fields = ['name']
    list_filter = ['is_popular']

@admin.register(UserPlan)
class UserPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'plan', 'is_active', 'activated_on']
    search_fields = ['user__username', 'plan__name']
    list_filter = ['is_active', 'activated_on']
