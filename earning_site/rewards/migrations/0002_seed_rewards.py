from decimal import Decimal

from django.db import migrations


def seed(apps, schema_editor):
    EarningTask = apps.get_model('rewards', 'EarningTask')
    MembershipPlan = apps.get_model('rewards', 'MembershipPlan')
    SpinReward = apps.get_model('rewards', 'SpinReward')

    MembershipPlan.objects.get_or_create(
        name='Free',
        defaults={
            'price': Decimal('0'),
            'duration_days': 3650,
            'daily_bonus': Decimal('5'),
            'task_multiplier': Decimal('1.00'),
            'max_daily_tasks': 5,
            'is_default': True,
        },
    )
    MembershipPlan.objects.get_or_create(
        name='Premium',
        defaults={
            'price': Decimal('999'),
            'duration_days': 30,
            'daily_bonus': Decimal('15'),
            'task_multiplier': Decimal('1.50'),
            'max_daily_tasks': 15,
            'faster_withdrawals': True,
        },
    )

    tasks = [
        ('Daily Login Bonus', 'login_bonus', '5', 'Claim your daily streak reward.', '', 1, 0, False),
        ('Watch Verified Ad', 'ad', '10', 'Watch the full ad timer before claiming.', '', 5, 30, False),
        ('Survey Partner Task', 'survey', '25', 'Complete a partner survey and submit proof if asked.', '', 3, 0, True),
        ('Offerwall Task', 'offerwall', '30', 'Complete an offerwall action from an approved partner.', '', 3, 0, True),
        ('App Install Task', 'app_install', '20', 'Install and open the listed app, then submit proof.', '', 2, 0, True),
        ('Invite a Friend', 'referral', '15', 'Invite a real user with your referral link.', '', 10, 0, True),
    ]
    for title, task_type, reward, instructions, external_url, daily_limit, duration, review in tasks:
        EarningTask.objects.get_or_create(
            title=title,
            defaults={
                'task_type': task_type,
                'reward_amount': Decimal(reward),
                'instructions': instructions,
                'external_url': external_url,
                'daily_limit': daily_limit,
                'duration_seconds': duration,
                'requires_review': review,
            },
        )

    for label, amount, weight in [
        ('Rs. 2 Bonus', '2', 45),
        ('Rs. 5 Bonus', '5', 30),
        ('Rs. 10 Bonus', '10', 15),
        ('Rs. 25 Bonus', '25', 7),
        ('Rs. 50 Jackpot', '50', 3),
    ]:
        SpinReward.objects.get_or_create(label=label, defaults={'amount': Decimal(amount), 'weight': weight})


class Migration(migrations.Migration):

    dependencies = [
        ('rewards', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
