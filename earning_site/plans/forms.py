from django import forms

class PaymentForm(forms.Form):
    PAYMENT_CHOICES = (
        ('JazzCash', 'JazzCash'),
        ('EasyPaisa', 'EasyPaisa'),
    )

    method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect,
        label="Select Payment Method"
    )
    phone_number = forms.CharField(
        max_length=15,
        label="Phone Number",
        widget=forms.TextInput(attrs={'placeholder': '03XXXXXXXXX'})
    )


class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        label='Enter OTP',
        widget=forms.TextInput(attrs={'placeholder': '6-digit code'})
    )
# plans/forms.py
from django import forms
from .models import Plan

class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ['name', 'price', 'duration_days', 'is_popular']
