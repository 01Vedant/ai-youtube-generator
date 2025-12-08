import os
import stripe

STRIPE_SECRET = os.getenv("STRIPE_SECRET", "")
STRIPE_PRICE_PRO = os.getenv("STRIPE_PRICE_PRO", "")  # price_...
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")

def client():
    if not STRIPE_SECRET:
        raise RuntimeError("STRIPE_SECRET missing")
    stripe.api_key = STRIPE_SECRET
    return stripe
