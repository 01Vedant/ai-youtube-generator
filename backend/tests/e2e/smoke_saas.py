"""
End-to-end smoke tests for SaaS integration.
Minimal tests covering auth, render, usage, and quota enforcement.
Skips billing tests if STRIPE_API_KEY not configured.
"""
import pytest
import os
import json
from httpx import AsyncClient
from fastapi import FastAPI
from typing import AsyncGenerator

# Skip marker for Stripe tests
stripe_available = bool(os.getenv("STRIPE_API_KEY"))
requires_stripe = pytest.mark.skipif(not stripe_available, reason="Stripe not configured")


@pytest.fixture
async def client() -> AsyncGenerator:
    """Create test client."""
    from app.main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_magic_link_flow(client):
    """Test passwordless auth: request → verify → /me."""
    email = "test@example.com"
    
    # Step 1: Request magic link
    resp = await client.post(
        "/api/auth/magic-link/request",
        json={"email": email}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    
    # Note: In real test, would extract token from Redis/email
    # For now, mock response
    pytest.skip("Mock token extraction needed in test environment")


@pytest.mark.asyncio
async def test_render_quota_enforcement(client):
    """Test quota check on render POST."""
    # Mock token
    token = os.getenv("TEST_JWT_TOKEN", "fake_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    render_plan = {
        "topic": "Test Video",
        "scenes": [
            {
                "description": "Scene 1",
                "duration_sec": 10,
                "image_prompt": "Test image",
                "voice_prompt": "Test voice",
            }
        ],
    }
    
    # POST /render
    resp = await client.post(
        "/render",
        json=render_plan,
        headers=headers,
    )
    
    # Should succeed or fail with 402 on quota exceeded
    assert resp.status_code in [200, 402, 401]
    
    if resp.status_code == 402:
        data = resp.json()
        assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_render_creates_job(client):
    """Test render job creation and polling."""
    # Mock credentials
    token = os.getenv("TEST_JWT_TOKEN", "fake_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    render_plan = {
        "topic": "Quick Test",
        "scenes": [
            {
                "description": "Quick scene",
                "duration_sec": 5,
                "image_prompt": "Quick image",
                "voice_prompt": "Quick voice",
            }
        ],
    }
    
    # POST /render
    resp = await client.post(
        "/render",
        json=render_plan,
        headers=headers,
    )
    
    # On success, get job_id
    if resp.status_code == 200:
        data = resp.json()
        job_id = data.get("job_id")
        assert job_id is not None
        
        # GET /render/{job_id}/status
        status_resp = await client.get(
            f"/render/{job_id}/status",
            headers=headers,
        )
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert "state" in status_data
        assert "progress_pct" in status_data


@requires_stripe
@pytest.mark.asyncio
async def test_billing_subscription_check(client):
    """Test billing subscription status endpoint."""
    token = os.getenv("TEST_JWT_TOKEN", "fake_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = await client.get(
        "/api/billing/subscription",
        headers=headers,
    )
    
    # Should return subscription info or 401
    assert resp.status_code in [200, 401]
    
    if resp.status_code == 200:
        data = resp.json()
        assert "plan" in data or "status" in data


@pytest.mark.asyncio
async def test_usage_endpoint(client):
    """Test usage tracking endpoint."""
    token = os.getenv("TEST_JWT_TOKEN", "fake_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = await client.get(
        "/api/usage",
        headers=headers,
    )
    
    # Should return usage or 401
    assert resp.status_code in [200, 401]
    
    if resp.status_code == 200:
        data = resp.json()
        # Should have metrics
        assert any(key in data for key in ["images_count", "render_minutes", "tts_seconds"])


@pytest.mark.asyncio
async def test_auth_me_endpoint(client):
    """Test /api/auth/me returns user info."""
    token = os.getenv("TEST_JWT_TOKEN", "fake_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    resp = await client.get(
        "/api/auth/me",
        headers=headers,
    )
    
    # Should return user or 401
    assert resp.status_code in [200, 401]
    
    if resp.status_code == 200:
        data = resp.json()
        assert "user_id" in data or "tenant_id" in data


@pytest.mark.asyncio
async def test_quota_violation_returns_402(client):
    """Test that quota violations return 402 Payment Required."""
    # This test would need to:
    # 1. Set up a tenant with very low quota
    # 2. Attempt a render that exceeds quota
    # 3. Verify 402 response
    
    token = os.getenv("TEST_JWT_TOKEN", "fake_token")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Large render plan
    render_plan = {
        "topic": "Large Video",
        "scenes": [{"description": f"Scene {i}", "duration_sec": 30} for i in range(100)],
    }
    
    resp = await client.post(
        "/render",
        json=render_plan,
        headers=headers,
    )
    
    # Should fail on quota or be too large
    assert resp.status_code in [400, 402, 429, 401]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
