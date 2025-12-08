from __future__ import annotations
from pathlib import Path
from typing import Any
import json

import importlib.util

from app.db import init_db, get_conn
import sys
from types import ModuleType

# Load billing routes directly
# Ensure stripe is stubbed before importing billing routes
if 'stripe' not in sys.modules:
    sys.modules['stripe'] = ModuleType('stripe')

_BILLING_PATH = Path(__file__).resolve().parents[1] / 'routes' / 'billing.py'
spec = importlib.util.spec_from_file_location("billing_router", str(_BILLING_PATH))
assert spec and spec.loader
billing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(billing)  # type: ignore


def _fake_user(uid: str, email: str) -> dict:
    return {"id": uid, "email": email, "plan_id": "free"}


def setup_user(uid: str, email: str):
    init_db()
    conn = get_conn()
    try:
        conn.execute("INSERT OR REPLACE INTO users (id, email, password_hash, created_at, plan_id) VALUES (?,?,?,?,?)",
                     (uid, email, "x", "", "free"))
        conn.commit()
    finally:
        conn.close()


def test_checkout_and_portal(monkeypatch):
    setup_user("u1", "u1@example.com")

    # Monkeypatch config and stripe client
    class StripeStub:
        class checkout:
            class Session:
                @staticmethod
                def create(**kwargs):
                    class S:
                        url = "https://stripe.test/checkout"
                    return S()
        class billing_portal:
            class Session:
                @staticmethod
                def create(**kwargs):
                    class P:
                        url = "https://stripe.test/portal"
                    return P()
        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return json.loads(payload.decode('utf-8'))
        class Subscription:
            @staticmethod
            def retrieve(sub_id):
                return {"id": sub_id, "status": "active", "current_period_end": 1700000000, "customer": "cus_123"}

    monkeypatch.setattr(billing, 'client', lambda: StripeStub())
    monkeypatch.setattr(billing, 'STRIPE_PRICE_PRO', 'price_123')
    monkeypatch.setattr(billing, 'STRIPE_WEBHOOK_SECRET', 'whsec_test')
    monkeypatch.setattr(billing, 'APP_BASE_URL', 'http://localhost:5173')

    # Checkout
    resp = billing.create_checkout_session(billing.CheckoutReq(plan_id="pro"), user=_fake_user("u1", "u1@example.com"))
    assert resp["url"].startswith("https://stripe.test/checkout")

    # Seed billing customer row for portal
    conn = get_conn()
    try:
        conn.execute("INSERT OR REPLACE INTO billing (user_id, stripe_customer_id, status) VALUES (?,?,?)", ("u1", "cus_123", "free"))
        conn.commit()
    finally:
        conn.close()

    # Portal
    resp2 = billing.create_portal_session(user=_fake_user("u1", "u1@example.com"))
    assert resp2["url"].startswith("https://stripe.test/portal")


def test_webhook_plan_flip(monkeypatch):
    setup_user("u2", "u2@example.com")
    # Prepare billing row
    conn = get_conn()
    try:
        conn.execute("INSERT OR REPLACE INTO billing (user_id, stripe_customer_id, status) VALUES (?,?,?)", ("u2", "cus_abc", "free"))
        conn.commit()
    finally:
        conn.close()

    class StripeStub:
        class Webhook:
            @staticmethod
            def construct_event(payload, sig, secret):
                return json.loads(payload.decode('utf-8'))
        class Subscription:
            @staticmethod
            def retrieve(sub_id):
                return {"id": sub_id, "status": "active", "current_period_end": 1700000000, "customer": "cus_abc"}

    monkeypatch.setattr(billing, 'client', lambda: StripeStub())
    monkeypatch.setattr(billing, 'STRIPE_WEBHOOK_SECRET', 'whsec_test')

    # checkout.session.completed -> set sub and pro plan
    evt = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_abc",
                "subscription": "sub_123",
                "customer_email": "u2@example.com",
            }
        }
    }

    class Req:
        def __init__(self, payload: bytes):
            self._p = payload
            self.headers = {"stripe-signature": "t=s,v1=sig"}
        async def body(self):
            return self._p

    req = Req(json.dumps(evt).encode('utf-8'))
    # Run webhook
    import asyncio
    asyncio.get_event_loop().run_until_complete(billing.stripe_webhook(req))

    # Verify pro
    conn = get_conn()
    try:
        row = conn.execute("SELECT plan_id FROM users WHERE id = ?", ("u2",)).fetchone()
        assert row and row[0] == 'pro'
    finally:
        conn.close()

    # customer.subscription.deleted -> revert to free
    evt2 = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_123", "customer": "cus_abc"}}
    }
    req2 = Req(json.dumps(evt2).encode('utf-8'))
    asyncio.get_event_loop().run_until_complete(billing.stripe_webhook(req2))

    conn = get_conn()
    try:
        row = conn.execute("SELECT plan_id FROM users WHERE id = ?", ("u2",)).fetchone()
        assert row and row[0] == 'free'
    finally:
        conn.close()
