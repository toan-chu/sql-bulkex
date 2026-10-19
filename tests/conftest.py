"""Pytest setup: no bytecode/cache files in the repo; make `import bulkex` work from app/."""
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
