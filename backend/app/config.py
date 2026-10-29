"""Local filesystem and application configuration."""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = (
    Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[2]
)
load_dotenv(PROJECT_ROOT / ".env", override=False)

_data_path = Path(os.environ.get("PHOTO_STUDIO_DATA_DIR", "data")).expanduser()
DATA_DIR = (_data_path if _data_path.is_absolute() else PROJECT_ROOT / _data_path).resolve()
DATABASE_PATH = DATA_DIR / "studio.sqlite3"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"
DEFAULT_OUTPUT_DIR = DATA_DIR / "documents"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
LEGAL_SOURCE = PROJECT_ROOT / "docs" / "reference" / "master_photography_services_agreement.md"
TEMPLATE_VERSION = "1.1.0"
