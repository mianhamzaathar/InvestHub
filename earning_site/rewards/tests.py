from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from wallet.models import Wallet
from .models import (
    AdvertiserProfile,
    Campaign,
    CampaignAction,
    DeviceToken,
    EarningTask,
    FraudSignal,
    ReferralCommission,
    ReferralProfile,
    TaskCompletion,
)
from .utils import get_device_key, record_campaign_action, run_user_fraud_checks


User = get_user_model()


def make_user(username, phone):
    return User.objects.create_user(username=username, phone_number=phone, password='secret123')


class RewardsPlatformTests(TestCase):
    def test_task_completion_credits_wallet_and_referrer(self):
        referrer = make_user('referrer', '03000000001')
        user = make_user('worker', '03000000002')
        profile = ReferralProfile.objects.get(user=user)
        profile.referred_by = referrer
        profile.save(update_fields=['referred_by'])
        task = EarningTask.objects.create(
            title='Watch sponsor',
            task_type='ad',
            reward_amount=Decimal('20.00'),
            duration_seconds=3,
        )

        client = Client(HTTP_HOST='localhost')
        client.force_login(user)
        response = client.post(reverse('rewards:complete_task', args=[task.id]), {'timer_seconds': '3'})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(TaskCompletion.objects.filter(user=user, task=task).count(), 1)
        self.assertEqual(Wallet.objects.get(user=user).balance, Decimal('20.00'))
        self.assertEqual(Wallet.objects.get(user=referrer).balance, Decimal('2.00'))
        self.assertEqual(ReferralCommission.objects.filter(referrer=referrer, referred_user=user).count(), 1)

    def test_short_timer_creates_high_fraud_signal(self):
        user = make_user('timeruser', '03000000003')
        task = EarningTask.objects.create(
            title='Timed action',
            task_type='ad',
            reward_amount=Decimal('10.00'),
            duration_seconds=30,
        )

        client = Client(HTTP_HOST='localhost')
        client.force_login(user)
        response = client.post(reverse('rewards:complete_task', args=[task.id]), {'timer_seconds': '2'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(FraudSignal.objects.filter(user=user, signal_type='task_timer_short', severity='high').exists())
        self.assertEqual(Wallet.objects.get(user=user).balance, Decimal('0.00'))

    def test_fraud_checks_flag_shared_device(self):
        first = make_user('firstdevice', '03000000004')
        second = make_user('seconddevice', '03000000005')
        task = EarningTask.objects.create(title='Simple task', task_type='ad', reward_amount=Decimal('5.00'))
        request = type('Request', (), {
            'META': {
                'HTTP_USER_AGENT': 'Mozilla',
                'HTTP_ACCEPT_LANGUAGE': 'en',
                'HTTP_SEC_CH_UA_PLATFORM': '',
                'REMOTE_ADDR': '127.0.0.1',
            },
        })()
        device_key = get_device_key(request)

        TaskCompletion.objects.create(user=first, task=task, reward_amount=Decimal('5.00'), device_key=device_key)
        TaskCompletion.objects.create(user=second, task=task, reward_amount=Decimal('5.00'), device_key=device_key)

        run_user_fraud_checks(second, request)
        self.assertTrue(FraudSignal.objects.filter(user=second, signal_type='shared_device_multiple_accounts').exists())

    def test_campaign_action_charges_budget_and_pays_user(self):
        advertiser_user = make_user('brand', '03000000006')
        worker = make_user('campaignworker', '03000000007')
        profile = AdvertiserProfile.objects.create(
            user=advertiser_user,
            company_name='Brand Co',
            contact_email='brand@example.com',
            balance=Decimal('500.00'),
            is_approved=True,
        )
        campaign = Campaign.objects.create(
            advertiser=profile,
            title='Install app',
            description='Install and open app',
            target_url='https://example.com',
            budget=Decimal('30.00'),
            reward_per_action=Decimal('30.00'),
            max_actions=1,
            status='active',
        )

        action = record_campaign_action(campaign, worker)
        campaign.refresh_from_db()

        self.assertIsNotNone(action)
        self.assertEqual(CampaignAction.objects.count(), 1)
        self.assertEqual(campaign.spent_amount, Decimal('30.00'))
        self.assertEqual(campaign.status, 'completed')
        self.assertEqual(Wallet.objects.get(user=worker).balance, Decimal('30.00'))

    def test_api_device_token_registration(self):
        user = make_user('mobileuser', '03000000008')
        client = Client(HTTP_HOST='localhost')
        client.force_login(user)

        response = client.post(reverse('api:device_token'), {'token': 'fcm-token-1', 'platform': 'android'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(DeviceToken.objects.filter(user=user, token='fcm-token-1', platform='android').exists())
