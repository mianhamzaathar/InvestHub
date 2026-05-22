# plans/jazzcash_api.py
import hashlib
import datetime
import random

MERCHANT_ID = "MC12345"
PASSWORD = "abc123"
INTEGRITY_SALT = "your_salt_here"
POST_URL = "https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform/"

def generate_transaction_id():
    return "T" + datetime.datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(100, 999))

def get_jazzcash_payload(amount, phone, return_url):
    txn_id = generate_transaction_id()
    txn_datetime = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    expiry = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime("%Y%m%d%H%M%S")

    payload = {
        "pp_Version": "1.1",
        "pp_TxnType": "MWALLET",
        "pp_Language": "EN",
        "pp_MerchantID": MERCHANT_ID,
        "pp_SubMerchantID": "",
        "pp_Password": PASSWORD,
        "pp_TxnRefNo": txn_id,
        "pp_Amount": str(int(amount * 100)),  # amount in paisa
        "pp_TxnCurrency": "PKR",
        "pp_TxnDateTime": txn_datetime,
        "pp_BillReference": "INV_" + txn_id,
        "pp_Description": "Plan Activation Payment",
        "pp_TxnExpiryDateTime": expiry,
        "pp_ReturnURL": return_url,
        "pp_SecureHash": "",  # to be calculated
        "ppmpf_1": phone,
        "ppmpf_2": "JazzCash",
    }

    # Secure Hash calculation
    sorted_keys = sorted(payload.keys())
    hash_string = INTEGRITY_SALT + '&' + '&'.join(str(payload[k]) for k in sorted_keys if k != 'pp_SecureHash')
    payload["pp_SecureHash"] = hashlib.sha256(hash_string.encode()).hexdigest().upper()

    return payload, POST_URL
