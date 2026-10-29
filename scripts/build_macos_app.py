"""Build a self-contained macOS app bundle for Finder installation."""

from __future__ import annotations

import errno
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
BUILD_DIR = ROOT / "build" / "macos_app"


def run(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> str:
    """Run a packaging step and preserve its output when diagnosing a build failure."""
    print("+", " ".join(command), flush=True)
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.returncode:
        raise RuntimeError(f"Build step failed with exit code {result.returncode}.")
    return result.stdout


def select_build_python() -> Path:
    """Choose the project virtual environment, honoring an explicit override."""
    configured = os.environ.get("PHOTO_STUDIO_PYTHON")
    if configured:
        executable = Path(configured).expanduser()
        if not executable.is_file():
            raise RuntimeError(
                "PHOTO_STUDIO_PYTHON does not point to a Python executable."
            )
        return executable.absolute()

    candidates = [ROOT / ".venv" / "bin" / "python", Path(sys.executable)]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.absolute()
    raise RuntimeError(
        "Python was not found. Create and activate the project virtual environment."
    )


def remove_generated_path(path: Path) -> None:
    """Remove one of this script's build outputs, tolerating Finder metadata files."""
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    if not path.exists():
        return

    def retry_remove(function, failing_path: str, error: OSError) -> None:
        failed = Path(failing_path)
        if failed.name == ".DS_Store":
            failed.unlink(missing_ok=True)
            return
        if error.errno == errno.ENOTEMPTY and failed.is_dir():
            for metadata in failed.glob(".DS_Store"):
                metadata.unlink(missing_ok=True)
            function(failing_path)
            return
        raise error

    shutil.rmtree(path, onexc=retry_remove)


def stage_playwright_browsers(python: Path, destination: Path) -> None:
    """Copy the installed headless Chromium runtime used for PDF rendering."""
    output = run(
        [str(python), "-m", "playwright", "install", "--dry-run", "chromium"],
        cwd=ROOT,
    )
    locations = re.findall(
        r"^\s*Install location:\s*(.+?)\s*$", output, flags=re.MULTILINE
    )
    required = [
        Path(location).expanduser()
        for location in locations
        if Path(location).name.startswith(("chromium_headless_shell-", "ffmpeg-"))
    ]
    if not required:
        raise RuntimeError(
            "Playwright did not report a Chromium installation location."
        )

    missing = [location for location in required if not location.is_dir()]
    if missing:
        missing_paths = "\n".join(f"  {path}" for path in missing)
        raise RuntimeError(
            "The matching Playwright Chromium files are not installed:\n"
            f"{missing_paths}\n"
            f"Install them with `{python} -m playwright install chromium`, then rebuild."
        )

    remove_generated_path(destination)
    destination.mkdir(parents=True)
    for source in required:
        target = destination / source.name
        shutil.copytree(
            source,
            target,
            symlinks=True,
            ignore=shutil.ignore_patterns(".DS_Store"),
        )
        print(f"Bundled Playwright browser: {source.name}", flush=True)


def stage_legacy_data_path(python: Path, destination: Path) -> None:
    """Record the old local data location so the installed app can import it once."""
    output = run(
        [
            str(python),
            "-c",
            "from backend.app.config import DATA_DIR; print(DATA_DIR)",
        ],
        cwd=ROOT,
    )
    configured_data_dir = Path(output.strip().splitlines()[-1]).expanduser().resolve()
    legacy_data_dir = (
        str(configured_data_dir)
        if (configured_data_dir / "studio.sqlite3").is_file()
        else ""
    )
    destination.write_text(legacy_data_dir, encoding="utf-8")
    if legacy_data_dir:
        print(
            "Existing local data will be imported on the app's first launch.",
            flush=True,
        )


def main() -> int:
    """Build the frontend, frozen backend, browser runtime, and Electron app bundle."""
    if sys.platform != "darwin":
        raise RuntimeError("The Finder-installable .app build must run on macOS.")

    python = select_build_python()
    npm = shutil.which("npm")
    builder = FRONTEND / "node_modules" / ".bin" / "electron-builder"
    if not npm:
        raise RuntimeError("Node.js and npm are required to build the macOS app.")
    if not builder.is_file():
        raise RuntimeError(
            "Electron Builder is not installed. Run `npm install --prefix frontend` first."
        )

    remove_generated_path(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True)
    backend_output = BUILD_DIR / "backend"
    browser_output = BUILD_DIR / "playwright"
    backend_output.mkdir(parents=True, exist_ok=True)
    pyinstaller_config = BUILD_DIR / "pyinstaller-config"
    pyinstaller_config.mkdir(parents=True, exist_ok=True)
    backend_executable = backend_output / "photography-document-studio-backend"
    if backend_executable.exists():
        backend_executable.unlink()

    run([npm, "run", "build", "--prefix", str(FRONTEND)], cwd=ROOT)
    stage_playwright_browsers(python, browser_output)
    stage_legacy_data_path(python, BUILD_DIR / "legacy_data_dir.txt")

    try:
        has_pyinstaller = (
            subprocess.run(
                [str(python), "-c", "import PyInstaller"],
                cwd=ROOT,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
    except OSError:
        has_pyinstaller = False
    if not has_pyinstaller:
        raise RuntimeError(
            "PyInstaller is not installed in the selected Python environment. "
            "Install `requirements-packaging.txt`, then rebuild."
        )

    package_data = [
        ("backend/app/templates", "backend/app/templates"),
        ("backend/alembic", "backend/alembic"),
        ("backend/alembic.ini", "backend"),
        ("frontend/dist", "frontend/dist"),
        (
            "docs/reference/master_photography_services_agreement.md",
            "docs/reference",
        ),
    ]
    freezer_command = [
        str(python),
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        "photography-document-studio-backend",
        "--distpath",
        str(backend_output),
        "--workpath",
        str(BUILD_DIR / "pyinstaller-work"),
        "--specpath",
        str(BUILD_DIR / "spec"),
        "--paths",
        str(ROOT),
    ]
    for source, target in package_data:
        freezer_command.extend(["--add-data", f"{ROOT / source}:{target}"])
    for module in ("backend.app", "backend.alembic.versions", "uvicorn"):
        freezer_command.extend(["--collect-submodules", module])
    freezer_command.extend(
        ["--collect-all", "playwright", str(ROOT / "scripts" / "electron_backend.py")]
    )
    freezer_environment = os.environ.copy()
    freezer_environment["PYINSTALLER_CONFIG_DIR"] = str(pyinstaller_config)
    run(freezer_command, cwd=ROOT, env=freezer_environment)

    machine = platform.machine().lower()
    architecture = "arm64" if machine in {"arm64", "aarch64"} else "x64"
    app_path = (
        ROOT / "release" / f"mac-{architecture}" / "Photography Document Studio.app"
    )
    remove_generated_path(app_path)
    run([str(builder), "--mac", "dir", f"--{architecture}"], cwd=FRONTEND)

    if not app_path.is_dir():
        candidates = sorted(
            (ROOT / "release").glob("**/Photography Document Studio.app")
        )
        if not candidates:
            raise RuntimeError(
                "Electron Builder finished without producing the expected .app bundle."
            )
        app_path = candidates[0]

    print("\nBuilt application:", app_path, flush=True)
    print(
        "Copy Photography Document Studio.app to /Applications to install it.",
        flush=True,
    )
    print(
        "This local ad-hoc signed build is intended for this Mac and is not notarized.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"macOS app build failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
