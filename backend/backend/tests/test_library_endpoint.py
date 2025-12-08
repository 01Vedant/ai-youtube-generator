"""
Unit tests for library endpoint
Tests schema validation and response structure
"""
import pytest
import requests
import json
import os
from pathlib import Path

# API base URL
API_BASE = "http://127.0.0.1:8000"


def test_library_response_shape():
    """Test that /library returns correct response shape with all required fields."""
    response = requests.get(f"{API_BASE}/library?page=1&pageSize=10")
    
    # Should return 200
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    
    data = response.json()
    
    # Response must have required top-level fields
    assert "entries" in data, "Response missing 'entries' field"
    assert "total" in data, "Response missing 'total' field"
    assert "page" in data, "Response missing 'page' field"
    assert "pageSize" in data, "Response missing 'pageSize' field"
    
    # Type checks
    assert isinstance(data["entries"], list), "entries must be a list"
    assert isinstance(data["total"], int), "total must be an integer"
    assert isinstance(data["page"], int), "page must be an integer"
    assert isinstance(data["pageSize"], int), "pageSize must be an integer"
    
    # Values should match query params
    assert data["page"] == 1, "page should be 1"
    assert data["pageSize"] == 10, "pageSize should be 10"
    
    print(f"✓ Library response has correct shape: {len(data['entries'])} entries, total={data['total']}")


def test_library_item_schema():
    """Test that each LibraryItem has correct schema."""
    response = requests.get(f"{API_BASE}/library?page=1&pageSize=5")
    assert response.status_code == 200
    
    data = response.json()
    entries = data["entries"]
    
    if len(entries) == 0:
        pytest.skip("No library entries to test (empty library)")
    
    # Check first entry
    item = entries[0]
    
    # Required fields
    assert "id" in item, "LibraryItem missing 'id' field"
    assert "title" in item, "LibraryItem missing 'title' field"
    assert "created_at" in item, "LibraryItem missing 'created_at' field"
    assert "state" in item, "LibraryItem missing 'state' field"
    
    # Type checks for required fields
    assert isinstance(item["id"], str), "id must be a string"
    assert isinstance(item["title"], str), "title must be a string"
    assert isinstance(item["created_at"], str), "created_at must be a string"
    assert isinstance(item["state"], str), "state must be a string"
    
    # Optional fields type checks (if present)
    if item.get("duration_sec") is not None:
        assert isinstance(item["duration_sec"], (int, float)), "duration_sec must be numeric"
    
    if item.get("voice") is not None:
        assert item["voice"] in ["Swara", "Diya"], "voice must be 'Swara' or 'Diya'"
    
    if item.get("template") is not None:
        assert isinstance(item["template"], str), "template must be a string"
    
    if item.get("thumbnail_url") is not None:
        assert isinstance(item["thumbnail_url"], str), "thumbnail_url must be a string"
    
    if item.get("video_url") is not None:
        assert isinstance(item["video_url"], str), "video_url must be a string"
    
    if item.get("error") is not None:
        assert isinstance(item["error"], str), "error must be a string"
    
    print(f"✓ LibraryItem schema valid: id={item['id'][:8]}, title={item['title'][:30]}, voice={item.get('voice')}")


def test_library_pagination():
    """Test that pagination parameters work correctly."""
    # Get page 1 with 5 items
    resp1 = requests.get(f"{API_BASE}/library?page=1&pageSize=5")
    assert resp1.status_code == 200
    
    data1 = resp1.json()
    
    # Page and pageSize should match
    assert data1["page"] == 1
    assert data1["pageSize"] == 5
    
    # Entries should not exceed pageSize
    assert len(data1["entries"]) <= 5, "entries should not exceed pageSize"
    
    # If there are more items, test page 2
    if data1["total"] > 5:
        resp2 = requests.get(f"{API_BASE}/library?page=2&pageSize=5")
        assert resp2.status_code == 200
        
        data2 = resp2.json()
        assert data2["page"] == 2
        assert data2["total"] == data1["total"], "total should be consistent across pages"
        
        # Entries on page 2 should be different from page 1
        if len(data1["entries"]) > 0 and len(data2["entries"]) > 0:
            ids1 = {e["id"] for e in data1["entries"]}
            ids2 = {e["id"] for e in data2["entries"]}
            assert ids1.isdisjoint(ids2), "page 1 and page 2 should have different entries"
        
        print(f"✓ Pagination works: page 1 has {len(data1['entries'])} items, page 2 has {len(data2['entries'])} items")
    else:
        print(f"✓ Pagination works: only {data1['total']} items (single page)")


def test_library_default_params():
    """Test that default parameters work (page=1, pageSize=20)."""
    response = requests.get(f"{API_BASE}/library")
    assert response.status_code == 200
    
    data = response.json()
    
    # Defaults should be applied
    assert data["page"] == 1, "default page should be 1"
    assert data["pageSize"] == 20, "default pageSize should be 20"
    
    print(f"✓ Default parameters work: page={data['page']}, pageSize={data['pageSize']}")


if __name__ == "__main__":
    # Can run directly for quick testing
    print("Running library endpoint tests...")
    test_library_response_shape()
    test_library_item_schema()
    test_library_pagination()
    test_library_default_params()
    print("✅ All library tests passed!")
