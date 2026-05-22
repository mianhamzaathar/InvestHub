# InvestHub Production Upgrade Notes

## Environment Variables

Set these before public launch:

```text
DJANGO_SECRET_KEY=
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_SECURE_COOKIES=True
DJANGO_SSL_REDIRECT=True
DJANGO_HSTS_SECONDS=31536000
DATABASE_URL=postgres://USER:PASSWORD@HOST:5432/investhub
REDIS_URL=redis://localhost:6379/1

PAYMENT_GATEWAY_MODE=live
JAZZCASH_MERCHANT_ID=
JAZZCASH_PASSWORD=
JAZZCASH_SALT=
EASYPAISA_STORE_ID=
EASYPAISA_HASH_KEY=
STRIPE_SECRET_KEY=

CPX_RESEARCH_APP_ID=
OFFERTORO_APP_ID=
ADGEM_APP_ID=
VPN_DETECTION_API_KEY=

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CSP_DEFAULT_SRC='self'
CSP_SCRIPT_SRC='self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com
CSP_STYLE_SRC='self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com
CSP_FONT_SRC='self' https://fonts.gstatic.com https://cdnjs.cloudflare.com
CSP_IMG_SRC='self' data: https:
```

## Added Production Foundations

- API base: `/api/v1/`
- Mobile/PWA device token endpoint: `/api/v1/device-token/`
- PWA: `/manifest.json`, `/sw.js`
- Advertiser panel: `/rewards/advertiser/`
- Staff analytics: `/rewards/admin-analytics/`
- Staff chart dashboard: `/rewards/analytics/`
- Advertiser wallet funding invoices and campaign budget/spend tracking
- Gateway transaction records for JazzCash/Easypaisa/Stripe hooks
- Integration provider registry in Django admin
- Audit logs for write actions
- Simple rate limiting middleware
- Security headers middleware with CSP/referrer/permissions headers
- Withdrawal OTP flow
- Celery-compatible task stubs in `rewards/tasks.py`
- Fraud checks for timer abuse, velocity spikes, shared IP/device, suspicious user agents

## External Integrations

Live provider calls are intentionally disabled until real credentials are configured. After credentials are set, implement provider-specific request/webhook code in:

- `payments/gateways.py`
- `payments/views.py`
- `rewards/tasks.py`

## Recommended Deployment

```text
Cloudflare
Nginx
Gunicorn
Django
PostgreSQL
Redis
Celery worker
Celery beat
```

Run workers:

```bash
celery -A earning_site worker -l info
celery -A earning_site beat -l info
```

Run validation before deploy:

```bash
python manage.py check
python manage.py test rewards wallet api
python manage.py migrate
```

## Compliance Notes

- Do not incentivize fake ad clicks.
- Use offerwall/survey postbacks for proof instead of trusting user screenshots.
- Keep earning rules visible.
- Keep withdrawal history visible.
- Review fraud flags before approving large withdrawals.
