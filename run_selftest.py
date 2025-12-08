"""
Standalone Self-Test Script
Run this directly with: python run_selftest.py
Tests the entire Bhakti Video Generator pipeline without needing the API server
"""
import sys
from pathlib import Path

# Add platform root to path
PLATFORM_ROOT = Path(__file__).resolve().parent / "platform"
sys.path.insert(0, str(PLATFORM_ROOT))

import os
os.chdir(PLATFORM_ROOT.parent)  # Set working directory to project root

# Import detector and run
from backend.app.env_detector import auto_configure_environment

print("\n" + "="*70)
print("BHAKTI VIDEO GENERATOR - STANDALONE SELF-TEST")
print("="*70 + "\n")

# Run environment detection
env_report = auto_configure_environment()

# Run simulator self-test
print("\nRunning simulator self-test...")
from orchestrator import run_selftest_simulated
sim_results = run_selftest_simulated()

# Print summary
print("\n" + "="*70)
print("SELF-TEST SUMMARY")
print("="*70)
print(f"\n✅ Environment Detection: {'PASSED' if env_report else 'FAILED'}")
print(f"✅ Simulator Test: {'PASSED' if sim_results.get('passed') else 'FAILED'}")

if sim_results.get('passed'):
    print(f"\n📊 Test Statistics:")
    print(f"   - Total tests: {len(sim_results.get('tests', []))}")
    print(f"   - Duration: {sim_results.get('duration_sec', 0):.2f}s")
    print(f"   - Job ID: {sim_results.get('job_id')}")

if sim_results.get('errors'):
    print(f"\n❌ Errors:")
    for error in sim_results['errors']:
        print(f"   - {error}")

print("\n" + "="*70)

# Try real orchestrator test if available
if not env_report['mode']['simulate_render']:
    print("\nAttempting real orchestrator test...")
    try:
        from pipeline.orchestrator import run_selftest_real
        real_results = run_selftest_real()
        print(f"✅ Real Orchestrator Test: {'PASSED' if real_results.get('passed') else 'FAILED'}")
    except ImportError:
        print("⚠️  Real orchestrator not available (expected in dev mode)")

print("\n✨ Self-test complete! You can now start the API server.")
print("   Run: python -m uvicorn app.main:app --reload")
print("   From: platform/backend/\n")
