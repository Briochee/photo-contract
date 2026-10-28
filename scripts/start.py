"""Start the built local application through one localhost FastAPI process."""

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--open", action="store_true", help="Open the local application in a browser"
    )
    args = parser.parse_args()
    frontend = ROOT / "frontend" / "dist" / "index.html"
    if not frontend.is_file():
        parser.error(
            "Frontend build is missing. Run `cd frontend && npm run build` first."
        )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "migrate.py")], cwd=ROOT, check=True
    )
    if args.open:
        webbrowser.open("http://127.0.0.1:8000")
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ],
        cwd=ROOT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
