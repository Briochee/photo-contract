"""Apply checked-in Alembic migrations to the configured local database."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env", override=False)
configured_data_dir = Path(os.environ.get("PHOTO_STUDIO_DATA_DIR", "data")).expanduser()
data_dir = (
    configured_data_dir
    if configured_data_dir.is_absolute()
    else ROOT / configured_data_dir
).resolve()
data_dir.mkdir(parents=True, exist_ok=True)
(data_dir / "documents").mkdir(parents=True, exist_ok=True)
(ROOT / "logs").mkdir(parents=True, exist_ok=True)

from backend.app.migrations import upgrade_database

try:
    upgrade_database()
except Exception as error:
    print(f"Database migration failed: {error}", file=sys.stderr)
    raise SystemExit(1) from error
