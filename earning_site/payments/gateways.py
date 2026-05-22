import hashlib
import uuid

from django.conf import settings


def jazzcash_payload(payment_log, return_url):
    txn_ref = f"IH-{uuid.uuid4().hex[:12].upper()}"
    payload = {
        'pp_Version': '1.1',
        'pp_TxnType': 'MWALLET',
        'pp_Language': 'EN',
        'pp_MerchantID': settings.JAZZCASH_MERCHANT_ID,
        'pp_Password': settings.JAZZCASH_PASSWORD,
        'pp_TxnRefNo': txn_ref,
        'pp_Amount': str(int(payment_log.amount * 100)),
        'pp_TxnCurrency': 'PKR',
        'pp_BillReference': f'INV-{payment_log.id}',
        'pp_Description': f'InvestHub activation for {payment_log.plan.name}',
        'pp_ReturnURL': return_url,
    }
    salt = settings.JAZZCASH_SALT
    hash_string = salt + '&' + '&'.join(str(payload[k]) for k in sorted(payload))
    payload['pp_SecureHash'] = hashlib.sha256(hash_string.encode()).hexdigest()
    return payload


def gateway_mode():
    return getattr(settings, 'PAYMENT_GATEWAY_MODE', 'manual_otp')


def gateway_configured(gateway):
    if gateway == 'JazzCash':
        return bool(settings.JAZZCASH_MERCHANT_ID and settings.JAZZCASH_MERCHANT_ID not in ('', 'YOUR_SANDBOX_MERCHANT_ID'))
    if gateway == 'EasyPaisa':
        return bool(getattr(settings, 'EASYPAISA_STORE_ID', ''))
    if gateway == 'Stripe':
        return bool(getattr(settings, 'STRIPE_SECRET_KEY', ''))
    return False
