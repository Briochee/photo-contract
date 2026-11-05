"""Require a synchronized app version newer than every published release tag."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_VERSION_PATTERN = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


def parse_version(value: str) -> tuple[int, int, int] | None:
    """Parse a stable semantic version or return None for unrelated Git tags."""
    match = _VERSION_PATTERN.fullmatch(value)
    return tuple(map(int, match.groups())) if match else None


def latest_release_version(tags: Iterable[str]) -> tuple[int, int, int] | None:
    """Find the highest stable version tag, accepting either `vX.Y.Z` or `X.Y.Z`."""
    versions = [version for tag in tags if (version := parse_version(tag)) is not None]
    return max(versions, default=None)


def validate_release_version(
    application_version: str,
    lockfile_version: str,
    lockfile_root_version: str,
    tags: Iterable[str],
) -> str:
    """Validate package/lockfile agreement and require a version newer than published tags."""
    current = parse_version(application_version)
    if current is None:
        raise ValueError(
            "frontend/package.json version must be stable semantic version X.Y.Z"
        )
    if (
        lockfile_version != application_version
        or lockfile_root_version != application_version
    ):
        raise ValueError(
            "frontend/package-lock.json must match the version in frontend/package.json"
        )

    latest = latest_release_version(tags)
    if latest is not None and current <= latest:
        rendered_latest = ".".join(map(str, latest))
        raise ValueError(
            f"Increment frontend/package.json above the latest release v{rendered_latest} "
            "before building. Update the npm lockfile in the same change."
        )
    return application_version


def main() -> int:
    """Print the validated release version for the GitHub Actions job output."""
    try:
        package = json.loads(
            (ROOT / "frontend/package.json").read_text(encoding="utf-8")
        )
        lockfile = json.loads(
            (ROOT / "frontend/package-lock.json").read_text(encoding="utf-8")
        )
        tags = subprocess.run(
            ["git", "tag", "--list"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        version = validate_release_version(
            package["version"],
            lockfile["version"],
            lockfile["packages"][""]["version"],
            tags,
        )
    except (
        KeyError,
        OSError,
        subprocess.CalledProcessError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"Release preflight failed: {exc}", file=sys.stderr)
        return 1
    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
