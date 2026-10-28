"""Import existing Streamlit JSON bookings and reference counters into SQLite."""

import json

from backend.app.database import SessionLocal
from backend.app.services.legacy_import import import_legacy


def main() -> None:
    with SessionLocal() as session:
        report = import_legacy(session)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
