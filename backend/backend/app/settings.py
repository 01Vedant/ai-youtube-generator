"""
Central configuration for artifact storage paths.
All pipeline outputs are stored under OUTPUT_ROOT.
"""

from pathlib import Path
import os

# Root of the backend/ directory
SETTINGS_ROOT = Path(__file__).resolve().parents[1]  # backend/

# Central output directory for all pipeline artifacts
OUTPUT_ROOT = SETTINGS_ROOT / "pipeline_outputs"
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

# Feature flags
FEATURE_TEMPLATES_MARKETPLACE = os.getenv("FEATURE_TEMPLATES_MARKETPLACE", "0") in ("1", "true", "True")
FEATURE_CANARY = os.getenv("FEATURE_CANARY", "0") in ("1", "true", "True")

# Feature flags
FEATURE_TEMPLATES_MARKETPLACE = os.getenv("FEATURE_TEMPLATES_MARKETPLACE", "0") in ("1", "true", "True")
