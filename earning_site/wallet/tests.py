from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Wallet, WithdrawalOTP, WithdrawalRequest


User = get_user_model()


class WithdrawalFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='withdrawer', phone_number='03100000001', password='secret123')
        self.wallet = Wallet.objects.get(user=self.user)
        self.wallet.credit(Decimal('500.00'), source='admin', description='Test funding')
        self.client = Client(HTTP_HOST='localhost')
        self.client.force_login(self.user)

    def test_first_withdrawal_post_generates_otp(self):
        response = self.client.post(reverse('withdraw'), {
            'amount': '100',
            'method': 'JazzCash',
            'account_number': '03001234567',
            'account_title': 'Test User',
        })

        self.assertEqual(response.status_code, 302)
        self.assertEqual(WithdrawalOTP.objects.filter(user=self.user, is_used=False).count(), 1)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal('500.00'))

    def test_valid_otp_creates_pending_withdrawal_and_debits_wallet(self):
        otp = WithdrawalOTP.objects.create(user=self.user, code='123456')

        response = self.client.post(reverse('withdraw'), {
            'amount': '150',
            'method': 'EasyPaisa',
            'account_number': '03001234567',
            'account_title': 'Test User',
            'otp_code': otp.code,
        })

        self.assertEqual(response.status_code, 302)
        self.wallet.refresh_from_db()
        otp.refresh_from_db()
        self.assertTrue(otp.is_used)
        self.assertEqual(self.wallet.balance, Decimal('350.00'))
        self.assertTrue(WithdrawalRequest.objects.filter(wallet=self.wallet, amount=Decimal('150.00'), status='pending').exists())
