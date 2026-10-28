"""Run the FastAPI and Vite development servers together."""

import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def main() -> int:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "migrate.py")], cwd=ROOT, check=True
    )
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.app.main:app",
                "--reload",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            cwd=ROOT,
        ),
        subprocess.Popen(
            ["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=FRONTEND
        ),
    ]
    try:
        while all(process.poll() is None for process in processes):
            time.sleep(0.4)
        return next(
            (
                process.returncode or 0
                for process in processes
                if process.poll() is not None
            ),
            0,
        )
    except KeyboardInterrupt:
        return 130
    finally:
        for process in processes:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
