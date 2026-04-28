import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

for source_dir in ("data-quality", "python-ingestor", "simulation-api"):
    source_path = str(REPO_ROOT / source_dir)
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
