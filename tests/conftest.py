import os
from pathlib import Path

# Set DB_PATH before any app modules are imported
os.environ.setdefault("DB_PATH", str(Path(__file__).parent / "test.db"))
