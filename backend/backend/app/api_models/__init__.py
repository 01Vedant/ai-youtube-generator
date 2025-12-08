"""Models package for API schemas."""

# Import all SQLAlchemy models from models.py (parent directory)
# This ensures backward compatibility with existing imports like "from app.models import JobStatus"
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
models_file = parent_dir / "models.py"

# Load models.py as a module and re-export its contents
import importlib.util
spec = importlib.util.spec_from_file_location("app.models_db", models_file)
models_db = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models_db)

# Re-export all classes from models.py
for name in dir(models_db):
    if not name.startswith("_"):
        globals()[name] = getattr(models_db, name)

# Export library-specific Pydantic models
from .library import LibraryItem, FetchLibraryResponse

__all__ = ["LibraryItem", "FetchLibraryResponse"]
