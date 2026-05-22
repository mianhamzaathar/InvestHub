import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'earning_site.settings')

try:
    from celery import Celery

    app = Celery('earning_site')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()
except Exception:
    app = None
