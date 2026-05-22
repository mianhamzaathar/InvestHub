from django import forms

class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Enter OTP'})
    )
from django import forms

class PaymentForm(forms.Form):
    phone = forms.CharField(max_length=15, required=True)
    method = forms.ChoiceField(
        choices=[
            ('JazzCash', 'JazzCash'),
            ('EasyPaisa', 'EasyPaisa'),
        ],
        required=True
    )
