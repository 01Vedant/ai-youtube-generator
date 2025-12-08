from fastapi import HTTPException
from app.db import init_db
from app.routes.public import post_waitlist
from types import SimpleNamespace

class FakeReq:
    def __init__(self, ip: str):
        self.client = SimpleNamespace(host=ip)

def test_waitlist_rl_and_duplicate():
    init_db()
    # Allow first insert
    assert post_waitlist({ 'email': 'rlcase@example.com' }, FakeReq('1.2.3.4'))['ok'] is True
    # Duplicate immediately may hit short RL; wait 16s to bypass 1/15s
    import time
    time.sleep(16)
    assert post_waitlist({ 'email': 'rlcase@example.com' }, FakeReq('1.2.3.4'))['duplicate'] is True
    # Hammer 12 requests should trigger RL
    caught = 0
    for _ in range(12):
        try:
            post_waitlist({ 'email': f'user{_}@example.com' }, FakeReq('9.9.9.9'))
        except HTTPException as e:
            if e.status_code == 429:
                detail = e.detail
                assert detail and detail.get('code') == 'QUOTA_EXCEEDED'
                caught += 1
                break
    assert caught == 1
